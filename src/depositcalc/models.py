"""Deposit data model — mirrors the input columns of the Excel workbook."""
from dataclasses import dataclass
from datetime import date


@dataclass
class Deposit:
    bank: str
    date_from: date
    date_to: date
    amount: float
    rate: float
    term_days: int
    inflation: float
    id: int | None = None
