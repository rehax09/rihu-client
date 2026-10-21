"""Microsoft / Minecraft sign-in.

How it works (this is the official flow):
  1. We open the real Microsoft login page in your normal web browser.
  2. You type your password THERE. The launcher never sees your password.
  3. Microsoft sends your browser back to a tiny local page (http://localhost:...)
     that carries a one-time code. We catch that code.
  4. The code is exchanged for Minecraft access. Minecraft ownership is checked by
     Mojang's servers. Nothing is bypassed.
  5. Only a refresh token is saved, inside Windows Credential Manager (via 'keyring').
"""
import inspect
import logging
import time
import webbrowser
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

import minecraft_launcher_lib as mll

try:
    import keyring
except ImportError:  # the launcher still works, it just can't remember you
    keyring = None

log = logging.getLogger("rihu.auth")
_SERVICE = "RihuClient"
_KEY = "microsoft_refresh_token"


class AuthError(Exception):
    """An error whose message is safe and helpful to show to the user."""


@dataclass
class Account:
    name: str
    uuid: str
    access_token: str


def _call(func, **values):
    """Call a library function with only the arguments its installed version accepts.
    (minecraft-launcher-lib changed some function signatures between releases.)"""
    accepted = inspect.signature(func).parameters
    return func(**{k: v for k, v in values.items() if k in accepted})


def _friendly(err: Exception) -> AuthError:
    kind = type(err).__name__
    if kind == "AzureAppNotPermitted":
        return AuthError(
            "Mojang has not approved your Azure application for Minecraft yet. "
            "Submit the approval form described in README.md (step 3), then wait for approval.")
    if kind in ("AccountNotOwnMinecraft", "AccountNotOwnGame"):
        return AuthError("This Microsoft account does not own Minecraft: Java Edition.")
    if kind == "XboxLiveNotAvailable" or "Xbox" in kind:
        return AuthError("Xbox Live sign-in failed (%s). Check that the account has an Xbox profile "
                         "and that Xbox services are available in your region." % kind)
    return AuthError("Sign-in failed (%s): %s" % (kind, err))


def _save_refresh_token(token: str) -> None:
    if keyring is None or not token:
        return
    try:
        keyring.set_password(_SERVICE, _KEY, token)
    except Exception as err:
        log.warning("Could not store token in Credential Manager: %s", err)


def _load_refresh_token():
    if keyring is None:
        return None
    try:
        return keyring.get_password(_SERVICE, _KEY)
    except Exception as err:
        log.warning("Could not read token from Credential Manager: %s", err)
        return None


def _to_account(login_data: dict) -> Account:
    return Account(name=login_data["name"], uuid=login_data["id"], access_token=login_data["access_token"])


def _wait_for_redirect(port: int, timeout: int = 180):
    """Run a tiny local web server until the browser comes back with the login code."""
    found = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if "code=" in self.path or "error=" in self.path:
                found["path"] = self.path
            body = ("<html><body style='font-family:Segoe UI,sans-serif;background:#0F0B1A;color:#EEEAFB;"
                    "text-align:center;padding-top:20vh'><h2>Signed in to Rihu Client Launcher</h2>"
                    "<p>You can close this tab and go back to the launcher.</p></body></html>").encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):  # keep the console quiet (the URL holds a one-time code)
            pass

    try:
        server = HTTPServer(("127.0.0.1", port), Handler)
    except OSError as err:
        raise AuthError("Port %d is already in use (%s). Close other launchers or change the port "
                        "in Settings." % (port, err))
    server.timeout = 2
    deadline = time.time() + timeout
    try:
        while "path" not in found and time.time() < deadline:
            server.handle_request()
    finally:
        server.server_close()
    return found.get("path")


def sign_in(client_id: str, redirect_uri: str) -> Account:
    """Interactive sign-in through the browser."""
    if not client_id.strip():
        raise AuthError("No Azure Client ID set. Open Settings and paste it in (see README.md, step 3).")
    port = urlparse(redirect_uri).port
    if not port:
        raise AuthError("The redirect address must include a port, e.g. http://localhost:53682")
    login_url, state, verifier = mll.microsoft_account.get_secure_login_data(client_id, redirect_uri)
    webbrowser.open(login_url)
    path = _wait_for_redirect(port)
    if not path:
        raise AuthError("Sign-in timed out. Press Play to try again.")
    full_url = redirect_uri.rstrip("/") + path
    try:
        auth_code = mll.microsoft_account.parse_auth_code_url(full_url, state)
    except (AssertionError, KeyError):
        raise AuthError("Sign-in was cancelled or the response did not match. Try again.")
    try:
        data = _call(mll.microsoft_account.complete_login, client_id=client_id, client_secret=None,
                     redirect_uri=redirect_uri, auth_code=auth_code, code_verifier=verifier)
    except Exception as err:
        log.exception("complete_login failed")
        raise _friendly(err)
    _save_refresh_token(data.get("refresh_token", ""))
    return _to_account(data)


def silent_sign_in(client_id: str, redirect_uri: str):
    """Sign in again using the saved refresh token. Returns None if that isn't possible."""
    token = _load_refresh_token()
    if not token or not client_id.strip():
        return None
    try:
        data = _call(mll.microsoft_account.complete_refresh, client_id=client_id, client_secret=None,
                     redirect_uri=redirect_uri, refresh_token=token)
    except Exception as err:
        log.info("Silent sign-in failed (%s); interactive sign-in will be needed.", type(err).__name__)
        return None
    _save_refresh_token(data.get("refresh_token", ""))
    return _to_account(data)


def sign_out() -> None:
    if keyring is None:
        return
    try:
        keyring.delete_password(_SERVICE, _KEY)
    except Exception:
        pass
