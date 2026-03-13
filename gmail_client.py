import base64
import os
from datetime import date, timedelta

from google.auth.credentials import Credentials as AuthCredentials
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from banks.base import BankScraper

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def authenticate() -> AuthCredentials:
    client_id = os.environ["G_OAUTH_CLIENT_ID"]
    client_secret = os.environ["G_OAUTH_CLIENT_SECRET"]
    refresh_token = os.environ.get("G_OAUTH_REFRESH_TOKEN")

    if refresh_token:
        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=SCOPES,
        )
        creds.refresh(Request())
        return creds

    # First-time setup: open browser to obtain a refresh token
    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uris": ["http://localhost:8080"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }
    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    creds = flow.run_local_server(port=8080, prompt="consent")
    if creds.refresh_token is None:
        print("\nWarning: no refresh token received. Re-run to try again.")
        return creds
    print(
        "\nFirst-time setup complete. Add this to your .env to skip the browser next time:"
    )
    print(f"G_OAUTH_REFRESH_TOKEN={creds.refresh_token}\n")
    return creds


class GmailClient:
    def __init__(self, creds: AuthCredentials) -> None:
        self._service = build("gmail", "v1", credentials=creds)

    def find_email(self, scraper: BankScraper) -> str | None:
        after = (date.today() - timedelta(days=scraper.days_lookback)).strftime("%Y/%m/%d")
        query = f'from:{scraper.search_from} subject:"{scraper.get_search_subject()}" after:{after}'
        result = (
            self._service.users()
            .messages()
            .list(userId="me", q=query, maxResults=1)
            .execute()
        )
        messages = result.get("messages", [])
        return messages[0]["id"] if messages else None

    def download_pdf_attachment(self, message_id: str) -> tuple[str, bytes] | None:
        message = (
            self._service.users()
            .messages()
            .get(userId="me", id=message_id, format="full")
            .execute()
        )
        parts = message.get("payload", {}).get("parts", [])

        for part in parts:
            mime = part.get("mimeType", "")
            filename = part.get("filename", "")
            if mime == "application/pdf" or filename.lower().endswith(".pdf"):
                attachment_id = part["body"].get("attachmentId")
                if attachment_id:
                    attachment = (
                        self._service.users()
                        .messages()
                        .attachments()
                        .get(userId="me", messageId=message_id, id=attachment_id)
                        .execute()
                    )
                    data = base64.urlsafe_b64decode(attachment["data"])
                    return filename, data

        return None
