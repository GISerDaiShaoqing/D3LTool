# -*- coding: utf-8 -*-
"""auth.login tests with a stubbed earthaccess module."""

import pytest

import d3ltool.auth as auth


class _StubEarthaccess:
    """Records what auth.py hands over and mimics login() outcomes."""

    def __init__(self, fail=False):
        self.calls = []
        self.environ_seen = {}
        self.fail = fail
        # mimics earthaccess.auth.authenticated
        self.auth = type("_A", (), {"authenticated": False})()

    def login(self, **kwargs):
        import os

        self.calls.append(kwargs)
        if self.fail:
            return None
        # mimic EnvironmentStrategy: reads EARTHDATA_* variables
        u = os.environ.get("EARTHDATA_USERNAME")
        p = os.environ.get("EARTHDATA_PASSWORD")
        if not (u and p):
            raise AssertionError("env vars not set with correct names")
        self.auth.authenticated = True
        return "environment"


def test_login_sets_correct_env_var_names(tmp_path, monkeypatch):
    monkeypatch.delenv("EARTHDATA_USERNAME", raising=False)
    monkeypatch.delenv("EARTHDATA_PASSWORD", raising=False)
    stub = _StubEarthaccess()
    monkeypatch.setattr(auth, "earthaccess", stub)

    user = auth.login("alice", "secret", persist=True)

    assert user == "alice"
    assert auth.current_user() == "alice"
    assert auth.is_authenticated() is True
    assert stub.calls == [{"strategy": "environment", "persist": True}]


def test_login_failure_raises_autherror(tmp_path, monkeypatch):
    stub = _StubEarthaccess(fail=True)
    monkeypatch.setattr(auth, "earthaccess", stub)
    monkeypatch.delenv("EARTHDATA_USERNAME", raising=False)
    monkeypatch.delenv("EARTHDATA_PASSWORD", raising=False)

    with pytest.raises(auth.AuthError):
        auth.login("bob", "wrong")


def test_empty_credentials_rejected(tmp_path, monkeypatch):
    stub = _StubEarthaccess()
    monkeypatch.setattr(auth, "earthaccess", stub)
    with pytest.raises(auth.AuthError):
        auth.login("", "pw")
    with pytest.raises(auth.AuthError):
        auth.login("user", "  ")
