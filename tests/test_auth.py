# -*- coding: utf-8 -*-
"""auth.login tests with a stubbed earthaccess module."""

import pytest

import d3ltool.auth as auth


class _StubEarthaccess:
    """Records what auth.py hands over and mimics login() outcomes."""

    def __init__(self, fail=False, raise_on_login=None):
        self.calls = []
        self.fail = fail
        self.raise_on_login = raise_on_login
        # mimics earthaccess.auth.authenticated
        self.auth = type("_A", (), {"authenticated": False})()

    def login(self, **kwargs):
        import os

        self.calls.append(kwargs)
        if self.raise_on_login is not None:
            raise self.raise_on_login
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


def test_bad_credentials_get_precise_message(tmp_path, monkeypatch):
    # earthaccess raises on invalid credentials (as 0.19 does); the URS probe
    # then confirms 401 so the dialog shows an actionable message
    stub = _StubEarthaccess(raise_on_login=RuntimeError(
        "Authentication with Earthdata Login failed with: invalid_credentials"))
    monkeypatch.setattr(auth, "earthaccess", stub)
    monkeypatch.setattr(auth, "_urs_probe", lambda u, p: "bad-credentials")

    with pytest.raises(auth.AuthError) as exc_info:
        auth.login("alice", "wrong")
    assert "401" in str(exc_info.value)


def test_probe_network_and_ok_paths(tmp_path, monkeypatch):
    stub = _StubEarthaccess(fail=True)
    monkeypatch.setattr(auth, "earthaccess", stub)

    monkeypatch.setattr(auth, "_urs_probe", lambda u, p: "network")
    with pytest.raises(auth.AuthError) as e1:
        auth.login("u", "p")
    assert "urs.earthdata" in str(e1.value)

    monkeypatch.setattr(auth, "_urs_probe", lambda u, p: "ok")
    with pytest.raises(auth.AuthError) as e2:
        auth.login("u", "p")
    assert str(e2.value) != str(e1.value)
