from .cmr import CMR
from .bchile import BCHILE
from .base import BankScraper

BANKS: list[BankScraper] = [CMR, BCHILE]
