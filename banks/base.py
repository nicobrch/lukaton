from dataclasses import dataclass
from typing import Callable


@dataclass
class BankScraper:
    """Configuration and credential logic for a single bank's statement scraping."""

    name: str
    search_from: str
    get_search_subject: Callable[[], str]
    get_pdf_password: Callable[[], str]
