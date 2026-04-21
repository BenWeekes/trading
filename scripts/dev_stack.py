#!/usr/bin/env python3
from __future__ import annotations

import argparse
import http.client
import json
import os
import re
import shutil
import signal
import socket
import ssl
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
RUN_DIR = ROOT / ".run"
LOG_DIR = RUN_DIR / "logs"
TUNNEL_URL_FILE = RUN_DIR / "cloudflared.url"
SAMPLE_ENV = ROOT / "agora-agent-samples" / "simple-backend" / ".env"


@dataclass(frozen=True)
class Service:
    name: str
    port: int
    cwd: Path
    cmd: list[str]
    health_url: str
    kill_patterns: tuple[str, ...] = ()

    @property
    def pidfile(self) -> Path:
        return RUN_DIR / f"{self.name}.pid"

    @property
    def logfile(self) -> Path:
        return LOG_DIR / f"{self.name}.log"


SERVICES = [
    Service(
        name="backend",
        port=8000,
        cwd=ROOT / "backend",
        cmd=[str(ROOT / ".venv" / "bin" / "uvicorn"), "app.main:app", "--reload", "--port", "8000"],
        health_url="http://localhost:8000/api/status",
        kill_patterns=("uvicorn app.main:app --reload --port 8000",),
    ),
    Service(
        name="frontend",
        port=3000,
        cwd=ROOT / "frontend",
        cmd=["npm", "run", "dev", "--", "--port", "3000"],
        health_url="http://localhost:3000",
        kill_patterns=(f"{ROOT}/frontend/node_modules/.bin/next dev",),
    ),
    Service(
        name="agora_backend",
        port=8082,
        cwd=ROOT / "agora-agent-samples" / "simple-backend",
        cmd=[str(ROOT / "agora-agent-samples" / "simple-backend" / "venv" / "bin" / "python"), "-u", "local_server.py"],
        health_url="http://localhost:8082/health",
        kill_patterns=("simple-backend/venv/bin/python -u local_server.py", "simple-backend local_server.py"),
    ),
    Service(
        name="avatar_client",
        port=8084,
        cwd=ROOT / "agora-agent-samples" / "react-video-client-avatar",
        cmd=["npm", "run", "dev"],
        health_url="http://localhost:8084",
        kill_patterns=(f"{ROOT}/agora-agent-samples/react-video-client-avatar/node_modules/.bin/next dev -p 8084",),
    ),
]

TUNNEL_CMD = ["cloudflared", "tunnel", "--url", "http://localhost:8000", "--no-autoupdate"]
TUNNEL_LOG = LOG_DIR / "cloudflared.log"
TUNNEL_PID = RUN_DIR / "cloudflared.pid"
TUNNEL_URL_RE = re.compile(r"https://[-a-z0-9]+\.trycloudflare\.com")


def print_line(message: str) -> None:
    print(message, flush=True)


def ensure_dirs() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.4)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def http_ok(url: str, *, method: str = "GET", body: bytes | None = None, headers: dict[str, str] | None = None, timeout: float = 10.0) -> tuple[bool, str]:
    try:
        req = Request(url, data=body, method=method)
        for key, value in (headers or {}).items():
            req.add_header(key, value)
        with urlopen(req, timeout=timeout) as response:
            preview = response.read(240).decode("utf-8", "ignore").strip().replace("\n", " ")
            return True, f"{response.status} {preview[:160]}"
    except HTTPError as exc:
        preview = exc.read(240).decode("utf-8", "ignore").strip().replace("\n", " ")
        return False, f"{exc.code} {preview[:160]}"
    except URLError as exc:
        return False, str(exc.reason)
    except Exception as exc:
        return False, str(exc)


def resolve_public_ip(host: str) -> str | None:
    for dns_server in ("1.1.1.1", "8.8.8.8"):
        proc = subprocess.run(
            ["nslookup", host, dns_server],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            continue
        for line in proc.stdout.splitlines():
            line = line.strip()
            if line.startswith("Address: ") and host not in line:
                return line.split("Address: ", 1)[1].strip()
    return None


def tunnel_http_ok(url: str, *, method: str = "GET", body: bytes | None = None, headers: dict[str, str] | None = None, timeout: float = 20.0) -> tuple[bool, str]:
    ok, status = http_ok(url, method=method, body=body, headers=headers, timeout=timeout)
    if ok or "nodename nor servname provided" not in status:
        return ok, status

    parts = urlsplit(url)
    host = parts.hostname
    if not host:
        return False, status
    ip = resolve_public_ip(host)
    if not ip:
        return False, status

    path = parts.path or "/"
    if parts.query:
        path = f"{path}?{parts.query}"
    context = ssl.create_default_context()
    try:
        with socket.create_connection((ip, parts.port or 443), timeout=timeout) as raw:
            with context.wrap_socket(raw, server_hostname=host) as sock:
                conn = http.client.HTTPSConnection(host=host, timeout=timeout)
                conn.sock = sock
                conn.request(method, path, body=body, headers=headers or {})
                response = conn.getresponse()
                preview = response.read(240).decode("utf-8", "ignore").strip().replace("\n", " ")
                conn.close()
                return response.status < 400, f"{response.status} {preview[:160]}"
    except Exception as exc:
        return False, str(exc)


def pid_from_file(path: Path) -> int | None:
    try:
        raw = path.read_text().strip()
        return int(raw) if raw else None
    except Exception:
        return None


def pid_running(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def terminate_pid(pid: int, *, wait_seconds: float = 8.0) -> None:
    pgid: int | None = None
    try:
        pgid = os.getpgid(pid)
    except Exception:
        pgid = None
    try:
        if pgid is not None:
            os.killpg(pgid, signal.SIGTERM)
        else:
            os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    except PermissionError:
        return
    deadline = time.time() + wait_seconds
    while time.time() < deadline:
        if not pid_running(pid):
            return
        time.sleep(0.2)
    try:
        if pgid is not None:
            os.killpg(pgid, signal.SIGKILL)
        else:
            os.kill(pid, signal.SIGKILL)
    except Exception:
        pass


def pids_on_port(port: int) -> list[int]:
    proc = subprocess.run(
        ["lsof", "-ti", f"tcp:{port}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    pids: list[int] = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            pids.append(int(line))
        except ValueError:
            pass
    return sorted(set(pids))


def kill_port(port: int) -> None:
    for pid in pids_on_port(port):
        terminate_pid(pid)
    deadline = time.time() + 8
    while time.time() < deadline:
        if not port_open(port):
            return
        time.sleep(0.2)


def kill_patterns(patterns: tuple[str, ...]) -> None:
    for pattern in patterns:
        subprocess.run(["pkill", "-f", pattern], cwd=ROOT, capture_output=True, text=True, check=False)


def start_process(cmd: list[str], cwd: Path, logfile: Path, pidfile: Path) -> int:
    with logfile.open("ab") as log:
        process = subprocess.Popen(
            cmd,
            cwd=str(cwd),
            stdout=log,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
            env=os.environ.copy(),
        )
    pidfile.write_text(str(process.pid))
    return process.pid


def ensure_service(service: Service, *, restart: bool = False) -> None:
    healthy, _ = http_ok(service.health_url)
    if healthy and not restart:
        return

    if restart:
        existing = pid_from_file(service.pidfile)
        if pid_running(existing):
            terminate_pid(existing)
        kill_patterns(service.kill_patterns)
        kill_port(service.port)
    elif port_open(service.port) and not healthy:
        kill_patterns(service.kill_patterns)
        kill_port(service.port)

    pid = start_process(service.cmd, service.cwd, service.logfile, service.pidfile)
    deadline = time.time() + 45
    last_status = "starting"
    while time.time() < deadline:
        healthy, last_status = http_ok(service.health_url)
        if healthy:
            print_line(f"{service.name}: up (pid {pid})")
            return
        time.sleep(1)
    raise RuntimeError(f"{service.name} failed health check: {last_status}. See {service.logfile}")


def read_tunnel_url() -> str | None:
    if TUNNEL_URL_FILE.exists():
        value = TUNNEL_URL_FILE.read_text().strip()
        if value:
            return value
    if TUNNEL_LOG.exists():
        match = TUNNEL_URL_RE.search(TUNNEL_LOG.read_text(errors="ignore"))
        if match:
            return match.group(0)
    return None


def kill_cloudflared() -> None:
    existing = pid_from_file(TUNNEL_PID)
    if pid_running(existing):
        terminate_pid(existing)
    proc = subprocess.run(
        ["pgrep", "-f", "cloudflared tunnel --url http://localhost:8000"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    for line in proc.stdout.splitlines():
        try:
            terminate_pid(int(line.strip()))
        except ValueError:
            pass


def start_tunnel(*, restart: bool = False) -> str:
    url = read_tunnel_url()
    if not restart and url:
        ok, _ = tunnel_http_ok(f"{url}/api/status")
        if ok:
            ok, _ = tunnel_http_ok(
                f"{url}/api/agora/chat/completions",
                method="POST",
                headers={"Content-Type": "application/json"},
                body=b'{"messages":[{"role":"user","content":"hello"}],"model":"gpt-4o-mini"}',
                timeout=20,
            )
            if ok:
                return url

    kill_cloudflared()
    TUNNEL_LOG.write_text("")
    if TUNNEL_URL_FILE.exists():
        TUNNEL_URL_FILE.unlink()
    pid = start_process(TUNNEL_CMD, ROOT, TUNNEL_LOG, TUNNEL_PID)
    deadline = time.time() + 45
    url = ""
    while time.time() < deadline:
        url = read_tunnel_url() or ""
        if url:
            ok, _ = tunnel_http_ok(f"{url}/api/status", timeout=20)
            if ok:
                ok, _ = tunnel_http_ok(
                    f"{url}/api/agora/chat/completions",
                    method="POST",
                    headers={"Content-Type": "application/json"},
                    body=b'{"messages":[{"role":"user","content":"hello"}],"model":"gpt-4o-mini"}',
                    timeout=20,
                )
                if ok:
                    TUNNEL_URL_FILE.write_text(url)
                    print_line(f"cloudflared: up (pid {pid}) {url}")
                    return url
        time.sleep(1)
    raise RuntimeError(f"cloudflared tunnel failed. See {TUNNEL_LOG}")


def update_env_line(path: Path, key: str, value: str) -> bool:
    if not path.exists():
        raise RuntimeError(f"Missing env file: {path}")
    lines = path.read_text().splitlines()
    updated = False
    found = False
    output: list[str] = []
    for line in lines:
        if line.startswith(f"{key}="):
            found = True
            desired = f"{key}={value}"
            output.append(desired)
            updated = updated or line != desired
        else:
            output.append(line)
    if not found:
        output.append(f"{key}={value}")
        updated = True
    if updated:
        path.write_text("\n".join(output) + "\n")
    return updated


def sync_agora_env(tunnel_url: str) -> bool:
    llm_url = f"{tunnel_url}/api/agora/chat/completions"
    changed = update_env_line(SAMPLE_ENV, "VIDEO_LLM_URL", llm_url)
    changed = update_env_line(SAMPLE_ENV, "VIDEO_LLM_VENDOR", "custom") or changed
    changed = update_env_line(SAMPLE_ENV, "VIDEO_LLM_STYLE", "openai") or changed
    changed = update_env_line(SAMPLE_ENV, "VIDEO_REGISTER_AGENT_URL", "http://localhost:8000/api/agora/register-agent") or changed
    return changed


def check_sample_backend_custom_llm() -> tuple[bool, str]:
    return http_ok("http://localhost:8082/start-agent?profile=VIDEO&connect=false", timeout=20)


def read_env_value(path: Path, key: str) -> str | None:
    if not path.exists():
        return None
    for line in path.read_text().splitlines():
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1].strip()
    return None


def verify_live_video_profile() -> None:
    req = Request("http://localhost:8082/start-agent?profile=VIDEO&debug=1", method="GET")
    with urlopen(req, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))

    tts_params = (
        data.get("debug", {})
        .get("agent_payload", {})
        .get("properties", {})
        .get("tts", {})
        .get("params", {})
    )
    avatar_params = (
        data.get("debug", {})
        .get("agent_payload", {})
        .get("properties", {})
        .get("avatar", {})
        .get("params", {})
    )

    expected_voice_id = read_env_value(SAMPLE_ENV, "VIDEO_TTS_VOICE_ID")
    expected_speed = read_env_value(SAMPLE_ENV, "VIDEO_TTS_SPEED")
    expected_avatar_id = read_env_value(SAMPLE_ENV, "VIDEO_AVATAR_ID")

    actual_voice_id = str(tts_params.get("voice_id", "")).strip()
    actual_speed = str(tts_params.get("speed", "")).strip()
    actual_avatar_id = str(avatar_params.get("avatar_id", "")).strip()

    mismatches: list[str] = []
    if expected_voice_id and actual_voice_id != expected_voice_id:
        mismatches.append(f"voice_id expected {expected_voice_id} got {actual_voice_id}")
    if expected_speed and actual_speed != expected_speed:
        mismatches.append(f"speed expected {expected_speed} got {actual_speed}")
    if expected_avatar_id and actual_avatar_id != expected_avatar_id:
        mismatches.append(f"avatar_id expected {expected_avatar_id} got {actual_avatar_id}")

    if mismatches:
        raise RuntimeError("live_video_profile failed: " + "; ".join(mismatches))

    print_line(f"live_video_profile: ok voice_id={actual_voice_id} speed={actual_speed} avatar_id={actual_avatar_id}")


def verify_stack(tunnel_url: str) -> None:
    checks = [
        ("frontend", "http://localhost:3000"),
        ("backend", "http://localhost:8000/api/status"),
        ("agora_backend", "http://localhost:8082/health"),
        ("avatar_client", "http://localhost:8084"),
        ("sample_token_bootstrap", "http://localhost:8082/start-agent?profile=VIDEO&connect=false"),
    ]
    for name, url in checks:
        ok, status = http_ok(url, timeout=20)
        if not ok:
            raise RuntimeError(f"{name} failed: {status}")
        print_line(f"{name}: ok")

    ok, status = tunnel_http_ok(
        f"{tunnel_url}/api/status",
        timeout=20,
    )
    if not ok:
        raise RuntimeError(f"tunnel_status failed: {status}")
    print_line("tunnel_status: ok")

    ok, status = tunnel_http_ok(
        f"{tunnel_url}/api/agora/chat/completions",
        method="POST",
        headers={"Content-Type": "application/json"},
        body=b'{"messages":[{"role":"user","content":"hello"}],"model":"gpt-4o-mini"}',
        timeout=20,
    )
    if not ok:
        raise RuntimeError(f"tunnel_chat_completions failed: {status}")
    print_line("tunnel_chat_completions: ok")

    verify_live_video_profile()


def do_up(*, restart: bool = False) -> None:
    ensure_dirs()
    ensure_service(SERVICES[0], restart=restart)
    tunnel_url = start_tunnel(restart=restart)
    env_changed = sync_agora_env(tunnel_url)
    ensure_service(SERVICES[1], restart=restart)
    ensure_service(SERVICES[2], restart=restart or env_changed)
    ensure_service(SERVICES[3], restart=restart)
    verify_stack(tunnel_url)
    print_line("")
    print_line("Ready:")
    print_line("  app:           http://localhost:3000")
    print_line("  backend:       http://localhost:8000/api/status")
    print_line("  agora backend: http://localhost:8082/health")
    print_line("  avatar client: http://localhost:8084")
    print_line(f"  tunnel:        {tunnel_url}")


def do_check() -> None:
    ensure_dirs()
    tunnel_url = read_tunnel_url()
    if not tunnel_url:
        raise RuntimeError("No tunnel URL recorded. Run `python scripts/dev_stack.py up` first.")
    verify_stack(tunnel_url)
    print_line(f"Ready: http://localhost:3000")


def do_down() -> None:
    ensure_dirs()
    for service in SERVICES:
        pid = pid_from_file(service.pidfile)
        if pid_running(pid):
            terminate_pid(pid)
        kill_port(service.port)
    kill_cloudflared()
    print_line("Stopped managed local stack.")


def main() -> int:
    if shutil.which("cloudflared") is None:
        print("Missing `cloudflared` on PATH.", file=sys.stderr)
        return 1

    parser = argparse.ArgumentParser(description="Start and verify the local trading + avatar stack.")
    sub = parser.add_subparsers(dest="command", required=True)
    up = sub.add_parser("up", help="Start services and verify the stack")
    up.add_argument("--restart", action="store_true", help="Force restart managed services")
    sub.add_parser("check", help="Verify the current stack")
    sub.add_parser("down", help="Stop managed services")
    args = parser.parse_args()

    try:
        if args.command == "up":
            do_up(restart=args.restart)
        elif args.command == "check":
            do_check()
        elif args.command == "down":
            do_down()
        else:
            parser.error("Unknown command")
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
