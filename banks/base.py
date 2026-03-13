from dataclasses import dataclass, field
from typing import Callable


@dataclass
class BankScraper:
    """Configuration and credential logic for a single bank's statement scraping."""

    name: str
    search_from: str
    get_search_subject: Callable[[], str]
    get_pdf_password: Callable[[], str]
    # How far back to search for the latest statement email.
    # 40 days covers any monthly billing cycle without matching older statements.
    days_lookback: int = field(default=40)
