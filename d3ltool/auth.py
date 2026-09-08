# -*- coding: utf-8 -*-
"""Earthdata Login via earthaccess. Search needs no auth; downloads do."""

import os

try:
    import earthaccess
except ImportError:  # GUI should still open without it
    earthaccess = None

_logged_in_user = {"name": ""}


class AuthError(RuntimeError):
    pass


def available() -> bool:
    return earthaccess is not None


def is_authenticated() -> bool:
    if earthaccess is None:
        return False
    try:
        return bool(earthaccess.auth.authenticated)
    except Exception:
        return False


def current_user() -> str:
    return _logged_in_user["name"]


def _call_login(**kwargs):
    """earthaccess.login(...) tolerating signature changes across versions."""
    try:
        return earthaccess.login(**kwargs)
    except TypeError:
        kwargs.pop("strategy", None)
        return earthaccess.login(**kwargs)


def login(username: str, password: str, persist: bool = True) -> str:
    """Login with credentials; returns the username on success.

    Credentials are handed to earthaccess through environment variables and,
    with persist=True, stored by earthaccess in the user's ~/.netrc.
    """
    if earthaccess is None:
        raise AuthError("earthaccess is not installed")
    username = (username or "").strip()
    password = password or ""
    if not username or not password:
        raise AuthError("empty username or password")

    os.environ["EDL_USERNAME"] = username
    os.environ["EDL_PASSWORD"] = password

    result = None
    try:
        result = _call_login(strategy="environment", persist=persist)
    except TypeError:
        result = _call_login(persist=persist)  # default order starts with environment
    if not result:
        try:
            result = _call_login(strategy="netrc", persist=persist)
        except TypeError:
            result = _call_login(persist=persist)
    if not result or not is_authenticated():
        raise AuthError("Earthdata rejected the credentials (or account lacks DAAC EULA approval)")
    _logged_in_user["name"] = username
    return username


def new_download_session():
    """An authenticated requests.Session for the download engine.

    Falls back to an anonymous session; downloads will then fail with 401
    and the UI prompts for login.
    """
    import requests

    if earthaccess is not None:
        try:
            return earthaccess.get_requests_https_session()
        except AttributeError:
            try:
                return earthaccess.auth.get_session()
            except Exception:
                pass
        except Exception:
            pass
    return requests.Session()
