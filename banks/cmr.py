import os

from .base import BankScraper


def _subject() -> str:
    # The stable subject prefix shared by all CMR billing cycle emails.
    # The full subject also contains the due date (e.g. "28 Febrero 2026"), which
    # varies each month — the `days_lookback` date filter on `BankScraper` ensures
    # only the current cycle's email is matched without needing to compute that date.
    return "Información CMR Mastercard Contactless Vencimiento"


def _password() -> str:
    rut = os.environ["RUT"]
    # Strip the hyphen then drop the last character (check digit).
    # e.g. "12345678-9" → "123456789" → "12345678"
    return rut.replace("-", "")[:-1]


CMR = BankScraper(
    name="CMR Falabella",
    search_from="EstadodeCuenta@cmr.cl",
    get_search_subject=_subject,
    get_pdf_password=_password,
)
