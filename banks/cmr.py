import os

from .base import BankScraper


def _subject() -> str:
    # CMR sends a new email per billing cycle with the due date in the subject.
    # TODO: compute this dynamically from the current billing cycle date.
    return "Información CMR Mastercard Contactless Vencimiento 28 Febrero 2026"


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
