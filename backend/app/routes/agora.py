from __future__ import annotations

import json
from collections.abc import AsyncGenerator

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

import httpx

from ..config import get_settings
from ..db.helpers import new_id, utcnow_iso
from ..db.repositories import (
    create_role_thread,
    get_recommendation,
    get_role_thread,
    insert_role_message,
    list_recommendations,
    list_role_messages,
    upsert_recommendation,
)
from ..roles import Orchestrator
from ..services.agora_bridge import trader_avatar_bridge
from ..services.discussion_subjects import ensure_recommendation_subject
from ..services.event_bus import event_bus
from ..services.voice_tools import (
    TOOL_DEFINITIONS,
    build_voice_context,
    execute_tool,
    get_active_rec_id,
    maybe_handle_direct_open_intent,
    maybe_handle_direct_pending_intent,
    set_active_context,
)

router = APIRouter(prefix="/api", tags=["agora"])
orchestrator = Orchestrator()


@router.get("/trader/avatar/status")
async def trader_avatar_status(recommendation_id: str | None = Query(default=None)):
    return trader_avatar_bridge.session_status(recommendation_id)


@router.post("/trader/avatar/start")
async def trader_avatar_start(payload: dict):
    recommendation_id = payload.get("recommendation_id")
    if not recommendation_id:
        raise HTTPException(status_code=400, detail="recommendation_id is required")
    if not get_recommendation(recommendation_id):
        raise HTTPException(status_code=404, detail="Recommendation not found")
    try:
        return await trader_avatar_bridge.start(recommendation_id, channel=payload.get("channel"))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/trader/avatar/speak")
async def trader_avatar_speak(payload: dict):
    recommendation_id = payload.get("recommendation_id")
    text = payload.get("text")
    if not recommendation_id or not text:
        raise HTTPException(status_code=400, detail="recommendation_id and text are required")
    try:
        return await trader_avatar_bridge.speak(recommendation_id, text, priority=payload.get("priority", "APPEND"))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/trader/avatar/stop")
async def trader_avatar_stop(payload: dict):
    recommendation_id = payload.get("recommendation_id")
    if not recommendation_id:
        raise HTTPException(status_code=400, detail="recommendation_id is required")
    try:
        return await trader_avatar_bridge.stop(recommendation_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/agora/chat/completions")
async def agora_chat_completions(payload: dict):
    """Custom LLM endpoint for Agora ConvoAI — uses function calling for all actions."""
    messages = payload.get("messages") or []
    if not messages:
        raise HTTPException(status_code=400, detail="messages are required")

    # Extract session info
    session_id = payload.get("channel") or payload.get("agent_uid") or "default"
    settings = get_settings()

    latest_user_text = next((m.get("content", "") for m in reversed(messages) if m.get("role") == "user"), "")
    direct_pending_result = await maybe_handle_direct_pending_intent(session_id, latest_user_text)
    if direct_pending_result is not None:
        await _persist_voice_turn(session_id, messages, direct_pending_result)
        return {
            "id": new_id("chatcmpl"),
            "object": "chat.completion",
            "created": int(__import__("time").time()),
            "model": payload.get("model") or settings.openai_model,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": direct_pending_result}, "finish_reason": "stop"}],
        }
    direct_open_result = await maybe_handle_direct_open_intent(session_id, latest_user_text)
    if direct_open_result is not None:
        await _persist_voice_turn(session_id, messages, direct_open_result)
        return {
            "id": new_id("chatcmpl"),
            "object": "chat.completion",
            "created": int(__import__("time").time()),
            "model": payload.get("model") or settings.openai_model,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": direct_open_result}, "finish_reason": "stop"}],
        }

    # Build context and inject as system message
    context_text = build_voice_context(session_id)

    # Prepare messages for OpenAI — replace/prepend system with our context
    llm_messages = []
    for m in messages:
        if m.get("role") == "system":
            continue  # skip original system message, we use ours
        llm_messages.append(m)
    llm_messages.insert(0, {"role": "system", "content": context_text})

    print(f"[agora-llm] session={session_id} msgs={len(llm_messages)} tools={len(TOOL_DEFINITIONS)}")

    # Call OpenAI with tools — multi-pass loop for tool execution
    model = payload.get("model") or settings.openai_model
    is_stream = payload.get("stream", False)
    final_content = ""

    for tool_pass in range(5):  # max 5 tool call rounds
        async with httpx.AsyncClient(timeout=90) as client:
            openai_payload = {
                "model": model,
                "messages": llm_messages,
                "tools": TOOL_DEFINITIONS,
                "tool_choice": "auto",
                "max_tokens": 300,
                "temperature": 0.7,
            }

            # Use Responses API for gpt-5+, Chat API for gpt-4
            if model.startswith("gpt-5") or model.startswith("gpt-6"):
                # For Responses API, convert to input format
                resp = await client.post(
                    "https://api.openai.com/v1/responses",
                    headers={"Authorization": f"Bearer {settings.openai_api_key}", "Content-Type": "application/json"},
                    json={
                        "model": model,
                        "instructions": context_text,
                        "input": _messages_to_input(llm_messages[1:]),  # skip system
                        "tools": [_convert_tool_for_responses(t) for t in TOOL_DEFINITIONS],
                        "max_output_tokens": 300,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                # Check for tool calls in output
                tool_calls = _extract_tool_calls_from_responses(data)
                if tool_calls:
                    results = await _execute_tool_calls(tool_calls, session_id)
                    # Add tool call + results to messages for next pass
                    llm_messages.append({"role": "assistant", "content": "", "tool_calls": tool_calls})
                    for tr in results:
                        llm_messages.append(tr)
                    continue
                final_content = data.get("output_text", "") or ""
                break
            else:
                # Standard Chat Completions API
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {settings.openai_api_key}", "Content-Type": "application/json"},
                    json=openai_payload,
                )
                resp.raise_for_status()
                data = resp.json()
                choice = data.get("choices", [{}])[0]
                msg = choice.get("message", {})

                if msg.get("tool_calls"):
                    tool_calls = msg["tool_calls"]
                    results = await _execute_tool_calls(tool_calls, session_id)
                    llm_messages.append(msg)
                    for tr in results:
                        llm_messages.append(tr)
                    continue

                final_content = msg.get("content", "")
                break

    # Persist the voice exchange into the same ticker thread as typed desk chat.
    await _persist_voice_turn(session_id, messages, final_content)

    if is_stream:
        return StreamingResponse(_stream_response(final_content, model), media_type="text/event-stream")

    return {
        "id": new_id("chatcmpl"),
        "object": "chat.completion",
        "created": int(__import__("time").time()),
        "model": model,
        "choices": [{"index": 0, "message": {"role": "assistant", "content": final_content}, "finish_reason": "stop"}],
    }


async def _execute_tool_calls(tool_calls: list[dict], session_id: str) -> list[dict]:
    """Execute tool calls and return tool result messages."""
    results = []
    for tc in tool_calls:
        fn = tc.get("function", {})
        name = fn.get("name", "")
        try:
            args = json.loads(fn.get("arguments", "{}"))
        except json.JSONDecodeError:
            args = {}
        print(f"[agora-llm] tool_call: {name}({json.dumps(args)[:100]})")
        result = await execute_tool(name, args, session_id)
        print(f"[agora-llm] tool_result: {result[:100]}")
        results.append({
            "role": "tool",
            "tool_call_id": tc.get("id", new_id("tc")),
            "name": name,
            "content": result,
        })
    return results


def _messages_to_input(messages: list[dict]) -> str:
    """Convert chat messages to a single input string for Responses API."""
    parts = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        if content:
            parts.append(f"{role}: {content}")
    return "\n".join(parts) if parts else "Hello"


def _convert_tool_for_responses(tool: dict) -> dict:
    """Convert Chat API tool format to Responses API format."""
    fn = tool.get("function", {})
    return {
        "type": "function",
        "name": fn.get("name"),
        "description": fn.get("description"),
        "parameters": fn.get("parameters"),
    }


def _extract_tool_calls_from_responses(data: dict) -> list[dict]:
    """Extract tool calls from Responses API output."""
    output = data.get("output", [])
    if not isinstance(output, list):
        return []
    tool_calls = []
    for item in output:
        if isinstance(item, dict) and item.get("type") == "function_call":
            tool_calls.append({
                "id": item.get("call_id", new_id("tc")),
                "type": "function",
                "function": {
                    "name": item.get("name", ""),
                    "arguments": item.get("arguments", "{}"),
                },
            })
    return tool_calls


async def _persist_voice_turn(session_id: str, messages: list[dict], content: str) -> None:
    """Persist the latest spoken user turn and trader reply into the active recommendation thread."""
    recommendation_id = get_active_rec_id(session_id)
    if not recommendation_id:
        return
    recommendation = get_recommendation(recommendation_id)
    if not recommendation:
        return
    subject = ensure_recommendation_subject(recommendation_id)
    thread = _ensure_trader_thread(recommendation["symbol"], recommendation_id)

    user_text = _latest_user_message(messages)
    if user_text:
        user_msg = _make_voice_message(
            thread_id=thread["id"],
            symbol=recommendation["symbol"],
            recommendation_id=recommendation_id,
            discussion_subject_id=subject["id"] if subject else None,
            sender="user",
            text=user_text,
            structured_payload={"type": "voice_user_message", "source": "agora", "session_id": session_id},
        )
        if not _is_duplicate_message(thread["id"], user_msg["sender"], user_msg["message_text"]):
            insert_role_message(user_msg)
            await event_bus.publish("role_message", user_msg)

    trader_text = (content or "").strip()
    if trader_text:
        trader_msg = _make_voice_message(
            thread_id=thread["id"],
            symbol=recommendation["symbol"],
            recommendation_id=recommendation_id,
            discussion_subject_id=subject["id"] if subject else None,
            sender="role:trader",
            text=trader_text,
            structured_payload={"type": "voice_response", "source": "agora", "session_id": session_id},
        )
        if not _is_duplicate_message(thread["id"], trader_msg["sender"], trader_msg["message_text"]):
            insert_role_message(trader_msg)
            await event_bus.publish("role_message", trader_msg)


def _ensure_trader_thread(symbol: str, recommendation_id: str) -> dict:
    thread = get_role_thread("trader", recommendation_id)
    if thread:
        return thread
    thread = {
        "id": new_id("thread"),
        "role": "trader",
        "symbol": symbol,
        "recommendation_id": recommendation_id,
        "created_at": utcnow_iso(),
    }
    create_role_thread(thread)
    return thread


def _make_voice_message(*, thread_id: str, symbol: str, recommendation_id: str, discussion_subject_id: str | None, sender: str, text: str, structured_payload: dict) -> dict:
    return {
        "id": new_id("msg"),
        "role_thread_id": thread_id,
        "role": "trader",
        "sender": sender,
        "symbol": symbol,
        "recommendation_id": recommendation_id,
        "discussion_subject_id": discussion_subject_id,
        "message_text": text,
        "structured_payload": structured_payload,
        "stance": None,
        "confidence": None,
        "provider": None,
        "model_used": None,
        "input_tokens": 0,
        "output_tokens": 0,
        "cost_usd": 0.0,
        "timestamp": utcnow_iso(),
    }


def _is_duplicate_message(thread_id: str, sender: str, text: str) -> bool:
    existing = list_role_messages(thread_id=thread_id)
    if not existing:
        return False
    last = existing[-1]
    return last.get("sender") == sender and (last.get("message_text") or "").strip() == text.strip()


def _latest_user_message(messages: list[dict]) -> str:
    for message in reversed(messages):
        if message.get("role") != "user":
            continue
        content = _message_text(message.get("content"))
        if content:
            return content
    return ""


def _message_text(content: object) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text") or item.get("content") or item.get("value")
                if isinstance(text, str):
                    parts.append(text)
        return " ".join(part.strip() for part in parts if part and part.strip()).strip()
    if isinstance(content, dict):
        text = content.get("text") or content.get("content") or content.get("value")
        if isinstance(text, str):
            return text.strip()
    return ""


async def _stream_response(content: str, model: str) -> AsyncGenerator[bytes, None]:
    chunk = {
        "id": new_id("chatcmpl"),
        "object": "chat.completion.chunk",
        "created": int(__import__("time").time()),
        "model": model,
        "choices": [{"index": 0, "delta": {"role": "assistant", "content": content}, "finish_reason": None}],
    }
    yield f"data: {json.dumps(chunk)}\n\n".encode()
    done = {
        "id": new_id("chatcmpl"),
        "object": "chat.completion.chunk",
        "created": int(__import__("time").time()),
        "model": model,
        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
    }
    yield f"data: {json.dumps(done)}\n\n".encode()
    yield b"data: [DONE]\n\n"
