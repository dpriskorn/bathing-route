import pytest
from pathlib import Path

from bathing_route.config import get_settings


def test_settings_defaults():
    settings = get_settings()
    assert settings.qlever_endpoint == "https://qlever.cs.uni-freiburg.de/api/wikidata"
    assert settings.wikimedia_bot_user == ""
    assert settings.wikimedia_bot_pass == ""


def test_settings_env_override(monkeypatch):
    monkeypatch.setenv("WIKIMEDIA_BOT_USER", "testuser")
    from bathing_route.config import get_settings
    settings = get_settings()
    assert settings.wikimedia_bot_user == "testuser"
