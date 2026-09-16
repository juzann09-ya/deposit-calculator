"""Pure financial formulas — a direct port of the Excel workbook's columns J-S.

No UI or storage dependencies here: this module is testable on desktop and
is the single source of truth for every derived number the app shows.
"""
from dataclasses import dataclass
from datetime import date

from depositcalc.models import Deposit


def _validate_term_days(term_days: int) -> None:
    if term_days <= 0:
        raise ValueError(f"term_days must be positive, got {term_days}")


def promised_income(amount: float, rate: float, term_days: int) -> float:
    """Excel column L: simple interest income over the term."""
    _validate_term_days(term_days)
    return amount * rate * (term_days / 365)


def nominal_total(amount: float, promised_income_value: float) -> float:
    """Excel column M."""
    return amount + promised_income_value


def nominal_growth(rate: float, term_days: int) -> float:
    """Excel column N."""
    _validate_term_days(term_days)
    return (1 + rate) ** (term_days / 365)


def nominal_yield(rate: float, term_days: int) -> float:
    """Excel column O."""
    return nominal_growth(rate, term_days) - 1


def inflation_growth(inflation: float, term_days: int) -> float:
    """Excel column P."""
    _validate_term_days(term_days)
    return (1 + inflation) ** (term_days / 365)


def inflation_over_term(inflation: float, term_days: int) -> float:
    """Excel column Q."""
    return inflation_growth(inflation, term_days) - 1


def real_yield(rate: float, inflation: float, term_days: int) -> float:
    """Excel column R: nominal growth deflated by inflation growth."""
    return nominal_growth(rate, term_days) / inflation_growth(inflation, term_days) - 1


def real_income_total(amount: float, rate: float, inflation: float, term_days: int) -> float:
    """Excel columns J/S (duplicated in the workbook)."""
    return amount * real_yield(rate, inflation, term_days)


def real_income_per_day(amount: float, rate: float, inflation: float, term_days: int) -> float:
    """Excel column K."""
    _validate_term_days(term_days)
    return real_income_total(amount, rate, inflation, term_days) / term_days


def portfolio_share(amount: float, total_amount: float) -> float:
    """Excel column A. Empty portfolio (total_amount == 0) yields 0, not a ZeroDivisionError."""
    if total_amount == 0:
        return 0.0
    return amount / total_amount


def days_to_close(date_to: date, today: date | None = None) -> int:
    """Excel column B. May be negative for already-closed deposits."""
    if today is None:
        today = date.today()
    return (date_to - today).days


def fire_4pct_annual(amount: float) -> float:
    return amount * 0.04


def fire_4pct_monthly(amount: float) -> float:
    return fire_4pct_annual(amount) / 12


def fire_3pct_annual(amount: float) -> float:
    return amount * 0.03


def fire_3pct_monthly(amount: float) -> float:
    return fire_3pct_annual(amount) / 12


@dataclass
class DepositMetrics:
    promised_income: float
    nominal_total: float
    nominal_growth: float
    nominal_yield: float
    inflation_growth: float
    inflation_over_term: float
    real_yield: float
    real_income_total: float
    real_income_per_day: float
    portfolio_share: float
    days_to_close: int
    fire_4pct_annual: float
    fire_4pct_monthly: float
    fire_3pct_annual: float
    fire_3pct_monthly: float


def compute_metrics(deposit: Deposit, portfolio_total: float, today: date | None = None) -> DepositMetrics:
    income = promised_income(deposit.amount, deposit.rate, deposit.term_days)
    return DepositMetrics(
        promised_income=income,
        nominal_total=nominal_total(deposit.amount, income),
        nominal_growth=nominal_growth(deposit.rate, deposit.term_days),
        nominal_yield=nominal_yield(deposit.rate, deposit.term_days),
        inflation_growth=inflation_growth(deposit.inflation, deposit.term_days),
        inflation_over_term=inflation_over_term(deposit.inflation, deposit.term_days),
        real_yield=real_yield(deposit.rate, deposit.inflation, deposit.term_days),
        real_income_total=real_income_total(deposit.amount, deposit.rate, deposit.inflation, deposit.term_days),
        real_income_per_day=real_income_per_day(deposit.amount, deposit.rate, deposit.inflation, deposit.term_days),
        portfolio_share=portfolio_share(deposit.amount, portfolio_total),
        days_to_close=days_to_close(deposit.date_to, today),
        fire_4pct_annual=fire_4pct_annual(deposit.amount),
        fire_4pct_monthly=fire_4pct_monthly(deposit.amount),
        fire_3pct_annual=fire_3pct_annual(deposit.amount),
        fire_3pct_monthly=fire_3pct_monthly(deposit.amount),
    )
