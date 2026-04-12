from __future__ import annotations

from .mock import MockProvider
from .openai_provider import OpenAIProvider


def get_provider(name: str):
    if name == "openai":
        return OpenAIProvider()
    return MockProvider()
