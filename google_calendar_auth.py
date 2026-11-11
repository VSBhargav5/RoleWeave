"""Browser consent via Google's maintained OAuth client, session-only credentials."""
import re

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google_calendar_sync import SCOPE, api_request
from network_io import Cancelled


class BoundedInstalledAppFlow(InstalledAppFlow):
    """The library's loopback timeout does not bound its token HTTPS exchange."""
    def fetch_token(self, **kwargs):
        kwargs["timeout"] = 5
        return super().fetch_token(**kwargs)


def connect_session(client_id, client_secret, *, confirmed=False, cancel=None):
    if confirmed is not True:
        raise ValueError("Review the app-created Calendar scope and consent before connecting")
    if not isinstance(client_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{8,250}\.apps\.googleusercontent\.com", client_id):
        raise ValueError("Enter your Google Desktop OAuth client ID in the app")
    if not isinstance(client_secret, str) or not 1 <= len(client_secret) <= 1000 or any(ord(c) < 33 or ord(c) > 126 for c in client_secret):
        raise ValueError("Enter the Desktop OAuth client secret in the masked app field")
    if cancel is not None and cancel.is_set():
        raise Cancelled("Connection cancelled locally")
    config = {"installed": {"client_id": client_id, "client_secret": client_secret,
                            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                            "token_uri": "https://oauth2.googleapis.com/token"}}
    try:
        flow = BoundedInstalledAppFlow.from_client_config(config, [SCOPE], autogenerate_code_verifier=True)
        flow.oauth2session.trust_env = False
        credentials = flow.run_local_server(host="127.0.0.1", bind_addr="127.0.0.1", port=0,
                                            open_browser=True, timeout_seconds=45,
                                            authorization_prompt_message="",
                                            success_message="RoleWeave consent received. Return to the app; no event was sent.",
                                            access_type="online", prompt="consent select_account",
                                            include_granted_scopes="false")
        scopes = set(credentials.granted_scopes or credentials.scopes or [])
        if scopes != {SCOPE} or not credentials.valid:
            raise ValueError("Unsupported or incomplete consent")
        if cancel is not None and cancel.is_set():
            raise Cancelled("Connection cancelled locally; revoke consent in Google if desired")
        # Do not retain refresh tokens, OAuth client secrets, flow objects or files.
        return Credentials(token=credentials.token, scopes=[SCOPE], expiry=credentials.expiry)
    except Cancelled:
        raise
    except Exception:
        raise ValueError("Google consent did not complete. Check Desktop client setup, test-user access and Calendar API enablement; no credential file was saved.") from None


def create_calendar(credentials, *, confirmed=False, cancel=None):
    if confirmed is not True:
        raise ValueError("Confirm creation of one app-owned RoleWeave Follow-ups calendar")
    result = api_request(credentials, "POST", "/calendar/v3/calendars",
                         body={"summary": "RoleWeave Follow-ups", "description": "Explicitly reviewed RoleWeave follow-up reminders. No automatic deletions."}, cancel=cancel)
    identifier = result.get("id")
    if not isinstance(identifier, str) or not identifier or identifier == "primary":
        raise ValueError("Calendar creation response could not be verified; inspect Google before retrying")
    return identifier
