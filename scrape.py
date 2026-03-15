from pathlib import Path

from dotenv import load_dotenv

from banks import BANKS
from banks.base import BankScraper
from client.gmail import GmailClient, authenticate
from utils.pdf import unlock_pdf

load_dotenv()


def scrape_bank(client: GmailClient, bank: BankScraper) -> None:
    print(f"\n[{bank.name}] Searching for statement email...")
    message_id = client.find_email(bank)
    if not message_id:
        print(f"[{bank.name}] Email not found.")
        return

    print(f"[{bank.name}] Found email (id={message_id}). Downloading PDF...")
    result = client.download_pdf_attachment(message_id)
    if not result:
        print(f"[{bank.name}] No PDF attachment found.")
        return

    filename, pdf_bytes = result
    print(f"[{bank.name}] Downloaded: {filename} ({len(pdf_bytes):,} bytes)")

    password = bank.get_pdf_password()
    output_path = Path(__file__).parent / "pdf" / filename
    output_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"[{bank.name}] Unlocking PDF...")
    unlock_pdf(pdf_bytes, password, output_path)
    print(f"[{bank.name}] Saved unlocked PDF to: {output_path.resolve()}")


def scrape() -> None:
    creds = authenticate()
    client = GmailClient(creds)
    for bank in BANKS:
        scrape_bank(client, bank)


if __name__ == "__main__":
    scrape()
