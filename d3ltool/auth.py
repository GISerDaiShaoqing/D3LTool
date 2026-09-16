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


def _urs_probe(username: str, password: str) -> str:
    """Ask URS directly what it thinks of the credential pair.

    Returns one of: "ok", "bad-credentials", "blocked", "network", "status-<n>".
    """
    import base64

    import requests

    try:
        pair = base64.b64encode(f"{username}:{password}".encode()).decode()
        resp = requests.post(
            "https://urs.earthdata.nasa.gov/api/users/token",
            headers={"Authorization": f"Basic {pair}"},
            timeout=30,
        )
    except requests.RequestException:
        return "network"
    if resp.status_code == 200:
        return "ok"
    if resp.status_code == 401:
        return "bad-credentials"
    if resp.status_code in (403, 429):
        return "blocked"
    return f"status-{resp.status_code}"


def login(username: str, password: str, persist: bool = True) -> str:
    """Login with credentials; returns the username on success.

    Credentials are handed to earthaccess through environment variables and,
    with persist=True, stored by earthaccess in the user's ~/.netrc.
    On failure, URS itself is probed so the error message says what actually
    went wrong (bad password vs blocked account vs network).
    """
    if earthaccess is None:
        raise AuthError("earthaccess is not installed")
    username = (username or "").strip()
    password = password or ""
    if not username or not password.strip():
        raise AuthError("empty username or password")

    os.environ["EARTHDATA_USERNAME"] = username
    os.environ["EARTHDATA_PASSWORD"] = password
    # older earthaccess releases read EDL_*; harmless to keep both
    os.environ["EDL_USERNAME"] = username
    os.environ["EDL_PASSWORD"] = password

    result = None
    error_text = ""
    for attempt in ({"strategy": "environment", "persist": persist}, {"persist": persist}):
        try:
            result = _call_login(**attempt)
            break
        except TypeError:
            continue     # parameter name not supported: try the plain call
        except Exception as exc:
            error_text = error_text or str(exc)
            break
    if not result:
        try:
            result = _call_login(strategy="netrc", persist=persist)
        except TypeError:
            try:
                result = _call_login(persist=persist)
            except Exception as exc:
                error_text = error_text or str(exc)
        except Exception as exc:
            error_text = error_text or str(exc)

    if result and is_authenticated():
        _logged_in_user["name"] = username
        return username

    # earthaccess could not complete the login: ask URS directly why
    from . import i18n

    verdict = _urs_probe(username, password)
    if verdict == "bad-credentials":
        raise AuthError(i18n.tr("auth_bad_credentials"))
    if verdict == "network":
        raise AuthError(i18n.tr("auth_network"))
    if verdict == "blocked":
        raise AuthError(i18n.tr("auth_blocked"))
    if verdict == "ok":
        raise AuthError(i18n.tr("auth_urs_ok_but_failed", detail=error_text[:300]))
    raise AuthError(i18n.tr("auth_earthaccess_generic",
                            detail=error_text[:300] or verdict))


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
