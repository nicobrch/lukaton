import base64
import io
import os
from pathlib import Path

from dotenv import load_dotenv
from google.auth.credentials import Credentials as AuthCredentials
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import pikepdf

load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
SEARCH_FROM = "EstadodeCuenta@cmr.cl"
SEARCH_SUBJECT = "Información CMR Mastercard Contactless Vencimiento 28 Febrero 2026"


def get_pdf_password() -> str:
    rut = os.environ["RUT"]
    without_hyphen = rut.replace("-", "")
    return without_hyphen[:-1]


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


def find_email(service) -> str | None:
    query = f'from:{SEARCH_FROM} subject:"{SEARCH_SUBJECT}"'
    result = (
        service.users().messages().list(userId="me", q=query, maxResults=1).execute()
    )
    messages = result.get("messages", [])
    if not messages:
        return None
    return messages[0]["id"]


def download_pdf_attachment(service, message_id: str) -> tuple[str, bytes] | None:
    message = (
        service.users()
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
                    service.users()
                    .messages()
                    .attachments()
                    .get(userId="me", messageId=message_id, id=attachment_id)
                    .execute()
                )
                data = base64.urlsafe_b64decode(attachment["data"])
                return filename, data

    return None


def unlock_pdf(pdf_bytes: bytes, password: str, output_path: Path) -> None:
    with pikepdf.open(io.BytesIO(pdf_bytes), password=password) as pdf:
        pdf.save(output_path)


def main() -> None:
    creds = authenticate()
    service = build("gmail", "v1", credentials=creds)

    print(f"Searching for email from {SEARCH_FROM}...")
    message_id = find_email(service)
    if not message_id:
        print("Email not found.")
        return

    print(f"Found email (id={message_id}). Downloading PDF attachment...")
    result = download_pdf_attachment(service, message_id)
    if not result:
        print("No PDF attachment found in the email.")
        return

    filename, pdf_bytes = result
    print(f"Downloaded: {filename} ({len(pdf_bytes):,} bytes)")

    password = get_pdf_password()
    output_path = Path(filename)
    print("Unlocking PDF...")
    unlock_pdf(pdf_bytes, password, output_path)
    print(f"Saved unlocked PDF to: {output_path.resolve()}")


if __name__ == "__main__":
    main()
