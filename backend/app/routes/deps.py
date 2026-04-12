from functools import lru_cache

from ..roles import Orchestrator


@lru_cache
def get_orchestrator() -> Orchestrator:
    return Orchestrator()
