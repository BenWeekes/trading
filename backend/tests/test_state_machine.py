import pytest

from app.services.state_machine import ensure_transition


def test_valid_transition():
    ensure_transition("observing", "under_discussion")


def test_invalid_transition():
    with pytest.raises(ValueError):
        ensure_transition("observing", "approved")
