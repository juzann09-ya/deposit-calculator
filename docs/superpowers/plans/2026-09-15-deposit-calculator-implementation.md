# Deposit Calculator (Android, Kivy) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the MVP Android deposit-portfolio calculator described in the design spec (revision 2) — a Kivy app that stores a portfolio of deposits locally, replicates the Excel workbook's income/inflation/FIRE formulas exactly, and matches the two fixed Figma mockups (portfolio grid, deposit detail) pixel-for-pixel in structure.

**Architecture:** A pure, UI-free `calc.py` ports every Excel formula 1:1 (TDD, verified against real values from the workbook) — carried over unchanged from the earlier Toga prototype (`worktree-deposit-calculator-mvp`), per spec §0/§3. `models.py` holds a plain `Deposit` dataclass, also unchanged. `storage.py` persists deposits in SQLite via the stdlib `sqlite3` module, unchanged except for where `main.py` points its db path (`App.user_data_dir` instead of Toga's `self.paths.data`). A Kivy UI layer draws the two fixed-mockup screens with hand-rolled `canvas` instructions (rounded rects, diagonal gradients via a 2×2 bilinear texture, dashed borders) inside `ScreenManager` screens, wired together by `main.py`. The whole app runs today via `python main.py` on the desktop (Kivy's default SDL2 window backend); Android packaging (Buildozer, Google Colab) is a separate, later step (§9 of the spec) the user runs herself and is not covered by this plan.

**Tech Stack:** Python 3.11+, Kivy (UI, `kivy[base]` pip extra), Buildozer (packaging config only — build itself runs in Google Colab, not here), stdlib `sqlite3`, pytest.

**Spec:** [docs/superpowers/specs/2026-09-15-deposit-calculator-design.md](../specs/2026-09-15-deposit-calculator-design.md) (revision 2, 2026-09-16)

## Global Constraints

- Exact formula fidelity: every derived metric must match spec §5 literally, including the two verification cases (`amount=100, rate=0.13, term_days=30, inflation=0.09` and the same with `term_days=365`). No capitalization, no deposits/withdrawals, no monthly schedule.
- `term_days` is always a manually-entered field on `Deposit` — never derived from `date_from`/`date_to`.
- Empty portfolio (`sum(amounts) == 0`) → `portfolio_share = 0`, never a `ZeroDivisionError`.
- `calc.py` has zero UI dependencies (no `kivy` import) so it can be unit-tested on desktop without a build.
- `term_days <= 0` passed directly to a `calc.py` formula function raises `ValueError` (the form itself must never let this happen, but the module must not silently divide by zero — spec §8).
- **The large number** on a portfolio card and in the detail hero is always `amount` (what the user deposited), never `nominal_total` (amount + interest). This is the bug fix from spec §0 — `nominal_total` still exists and is used only inside the "Рассчитывается автоматически" section, never as the card/hero headline figure.
- **Design is fixed by mockup, not by taste.** The portfolio screen (`docs/superpowers/design/01 Портфель.png`) and detail screen (`docs/superpowers/design/Калькулятор вкладов — дизайн.png`, right frame) are approved and must be followed for block structure, field order/grouping, and the single-badge-on-card / two-badges-in-hero rule (spec §6.1, §6.2, §6.3). The add/edit form (§6.4) has no mockup — it is built from the prose description only, in the same visual language (rounded inputs, muted labels, one accent button).
- UI layer (Kivy widgets) has **no automated tests in the MVP** — spec §8 explicitly calls this out. UI tasks are verified manually by running `python main.py` on the desktop instead of pytest.
- Bank→gradient hashing must be **stable across process restarts** — do not use Python's built-in `hash()` on strings (it is salted per-process by default); use `zlib.crc32`.
- Kivy's stock font may not have full Cyrillic coverage in every environment. `main.py` registers a system font (`arial.ttf` on Windows, which has full Cyrillic support) as the `"Roboto"` family — the name Kivy widgets use as their default font — before any widget is created, guarded by an `os.path.exists` check so it's a no-op (falls back to Kivy's stock font) on a machine without that path. Bundling a Cyrillic-capable font *inside* the Android APK is left to the separate Buildozer/Colab walkthrough document (spec §9) — out of scope here.
- Kivy `Label.halign` has **no visible effect** unless `text_size` is bound to the label's own `size` first (otherwise the text texture is centered in the widget regardless of `halign`). Every left-aligned label in this plan uses the `left_label()` helper from Task 6, which wires this up once so screen code never has to think about it again.
- Package name: `depositcalc`. Bundle id: `dev.chesterjuz`. App title: "Калькулятор вкладов".
- Android packaging steps (`buildozer android debug` and everything after) and their troubleshooting are explicitly out of scope for this plan — spec §9 says that gets a separate document later, written by/for the user's own Google Colab run.

---

### Task 1: Project scaffolding (Kivy, no Briefcase/Toga)

**Files:**
- Create: `main.py`
- Create: `src/depositcalc/__init__.py`
- Create: `src/depositcalc/ui/__init__.py`
- Create: `tests/__init__.py`
- Create: `pytest.ini`
- Create: `.gitignore`
- Create: `buildozer.spec`

**Interfaces:**
- Consumes: nothing (first task).
- Produces: a runnable Kivy window (`python main.py` opens it, Cyrillic renders correctly), a pytest setup that imports `depositcalc` from `src/` without installation, and a committed `buildozer.spec` skeleton. Task 10 modifies `main.py` to replace the placeholder window content with the real `ScreenManager` wiring — the font-registration and `sys.path` lines added here stay untouched.

- [ ] **Step 1: Create the directory layout and empty package markers**

```bash
mkdir -p src/depositcalc/ui tests
touch src/depositcalc/__init__.py src/depositcalc/ui/__init__.py tests/__init__.py
```

- [ ] **Step 2: Write `pytest.ini`**

```ini
[pytest]
pythonpath = src
testpaths = tests
```

- [ ] **Step 3: Write the placeholder `main.py`**

This is the app's real entry point from day one (Buildozer looks for exactly this file at the repo root). Task 10 replaces the body of `build()` with the full `ScreenManager`/storage wiring; the `sys.path` and font-registration lines at the top are permanent.

```python
"""Kivy App entry point. Buildozer packages the repo with this file at the root.

Full screen/storage wiring lands in Task 10 of the implementation plan.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from kivy.core.text import LabelBase  # noqa: E402  (must run before any widget is built)

_WINDOWS_CYRILLIC_FONT = r"C:\Windows\Fonts\arial.ttf"
if os.path.exists(_WINDOWS_CYRILLIC_FONT):
    # Overrides Kivy's default "Roboto" font family with one that reliably
    # renders Cyrillic on this desktop dev machine. See Global Constraints.
    LabelBase.register(name="Roboto", fn_regular=_WINDOWS_CYRILLIC_FONT)

from kivy.app import App  # noqa: E402
from kivy.uix.label import Label  # noqa: E402


class DepositCalculatorApp(App):
    def build(self):
        self.title = "Калькулятор вкладов"
        return Label(text="Калькулятор вкладов", font_size=20)


if __name__ == "__main__":
    DepositCalculatorApp().run()
```

- [ ] **Step 4: Write `.gitignore`**

```
.venv/
__pycache__/
*.pyc
.pytest_cache/
*.db
.buildozer/
bin/
```

- [ ] **Step 5: Create a virtual environment and install tooling**

```bash
python -m venv .venv
.venv/Scripts/pip install "kivy[base]" pytest
```

- [ ] **Step 6: Verify the app runs and Cyrillic renders correctly**

```bash
.venv/Scripts/python main.py
```

Expected: a window opens showing the text "Калькулятор вкладов" in readable Cyrillic (no tofu/blank boxes). Close the window to return control. No tracebacks in the console. If the text does *not* render (rare — only if `arial.ttf` isn't at the path above on this machine), stop and fix the font path in `main.py` before continuing; every later task's screens depend on Cyrillic rendering correctly.

- [ ] **Step 7: Verify pytest can run (no tests yet, should collect zero and exit cleanly)**

```bash
.venv/Scripts/pytest
```

Expected: `no tests ran` (exit code 0 or 5 — either is fine at this stage; it confirms `pytest.ini`'s config is valid).

- [ ] **Step 8: Write `buildozer.spec`**

Hand-authored rather than generated by `buildozer init` (which would require installing Buildozer locally, unnecessary since the user builds in Google Colab per spec §9). This is a minimal-but-complete spec; the Colab walkthrough document (spec §9, written later) may add more keys (icon, presplash, android.arch, etc.) as needed once the user actually runs a build.

```ini
[app]
title = Калькулятор вкладов
package.name = depositcalc
package.domain = dev.chesterjuz
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf
version = 0.1.0
requirements = python3,kivy
orientation = portrait
fullscreen = 0

[buildozer]
log_level = 2
warn_on_root = 1
```

- [ ] **Step 9: Commit**

```bash
git add main.py pytest.ini .gitignore buildozer.spec src tests
git commit -m "Scaffold Kivy project skeleton"
```

---

### Task 2: Core financial formulas (`calc.py`)

**Files:**
- Create: `src/depositcalc/calc.py`
- Create: `tests/test_calc.py`

**Interfaces:**
- Consumes: nothing (pure functions over primitives, no `Deposit` dependency yet).
- Produces (consumed by Task 3's `compute_metrics`):
  - `_validate_term_days(term_days: int) -> None` (raises `ValueError` if `term_days <= 0`)
  - `promised_income(amount: float, rate: float, term_days: int) -> float`
  - `nominal_total(amount: float, promised_income_value: float) -> float`
  - `nominal_growth(rate: float, term_days: int) -> float`
  - `nominal_yield(rate: float, term_days: int) -> float`
  - `inflation_growth(inflation: float, term_days: int) -> float`
  - `inflation_over_term(inflation: float, term_days: int) -> float`
  - `real_yield(rate: float, inflation: float, term_days: int) -> float`
  - `real_income_total(amount: float, rate: float, inflation: float, term_days: int) -> float`
  - `real_income_per_day(amount: float, rate: float, inflation: float, term_days: int) -> float`
  - `portfolio_share(amount: float, total_amount: float) -> float`
  - `days_to_close(date_to: date, today: date | None = None) -> int`
  - `fire_4pct_annual(amount: float) -> float`, `fire_4pct_monthly(amount: float) -> float`
  - `fire_3pct_annual(amount: float) -> float`, `fire_3pct_monthly(amount: float) -> float`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_calc.py
from datetime import date

import pytest

from depositcalc import calc


def test_promised_income_excel_case_30_days():
    result = calc.promised_income(amount=100, rate=0.13, term_days=30)
    assert result == pytest.approx(100 * 0.13 * 30 / 365, rel=1e-9)


def test_nominal_total_adds_income_to_principal():
    assert calc.nominal_total(100, 1.5) == 101.5


def test_nominal_growth_matches_excel_30_days():
    assert calc.nominal_growth(rate=0.13, term_days=30) == pytest.approx(1.010096, abs=1e-5)


def test_nominal_yield_matches_excel_30_days():
    assert calc.nominal_yield(rate=0.13, term_days=30) == pytest.approx(0.010096, abs=1e-5)


def test_nominal_growth_full_year_equals_rate_plus_one():
    assert calc.nominal_growth(rate=0.13, term_days=365) == pytest.approx(1.13, abs=1e-9)


def test_inflation_growth_matches_excel_30_days():
    assert calc.inflation_growth(inflation=0.09, term_days=30) == pytest.approx(1.007108, abs=1e-5)


def test_inflation_over_term_matches_excel_30_days():
    assert calc.inflation_over_term(inflation=0.09, term_days=30) == pytest.approx(0.007108, abs=1e-5)


def test_real_yield_matches_excel_30_days():
    assert calc.real_yield(rate=0.13, inflation=0.09, term_days=30) == pytest.approx(0.0029666, abs=1e-6)


def test_real_yield_matches_excel_365_days():
    assert calc.real_yield(rate=0.13, inflation=0.09, term_days=365) == pytest.approx(0.0366972, abs=1e-6)


def test_real_income_total_matches_excel_30_days():
    result = calc.real_income_total(amount=100, rate=0.13, inflation=0.09, term_days=30)
    assert result == pytest.approx(0.296658, abs=1e-4)


def test_real_income_total_matches_excel_365_days():
    result = calc.real_income_total(amount=100, rate=0.13, inflation=0.09, term_days=365)
    assert result == pytest.approx(3.669725, abs=1e-4)


def test_real_income_per_day_divides_total_by_term():
    total = calc.real_income_total(amount=100, rate=0.13, inflation=0.09, term_days=30)
    per_day = calc.real_income_per_day(amount=100, rate=0.13, inflation=0.09, term_days=30)
    assert per_day == pytest.approx(total / 30)


def test_portfolio_share_of_two_equal_deposits():
    assert calc.portfolio_share(amount=100, total_amount=200) == 0.5


def test_portfolio_share_empty_portfolio_returns_zero():
    assert calc.portfolio_share(amount=0, total_amount=0) == 0.0


def test_days_to_close_future_date_is_positive():
    today = date(2026, 1, 1)
    assert calc.days_to_close(date_to=date(2026, 1, 31), today=today) == 30


def test_days_to_close_past_date_is_negative():
    today = date(2026, 1, 31)
    assert calc.days_to_close(date_to=date(2026, 1, 1), today=today) == -30


def test_zero_rate_gives_zero_nominal_yield():
    assert calc.nominal_yield(rate=0.0, term_days=30) == pytest.approx(0.0)


def test_zero_inflation_gives_zero_inflation_over_term():
    assert calc.inflation_over_term(inflation=0.0, term_days=30) == pytest.approx(0.0)


def test_promised_income_rejects_zero_term_days():
    with pytest.raises(ValueError):
        calc.promised_income(amount=100, rate=0.13, term_days=0)


def test_nominal_growth_rejects_negative_term_days():
    with pytest.raises(ValueError):
        calc.nominal_growth(rate=0.13, term_days=-1)


def test_inflation_growth_rejects_zero_term_days():
    with pytest.raises(ValueError):
        calc.inflation_growth(inflation=0.09, term_days=0)


def test_real_income_per_day_rejects_zero_term_days():
    with pytest.raises(ValueError):
        calc.real_income_per_day(amount=100, rate=0.13, inflation=0.09, term_days=0)


def test_fire_4pct_annual_and_monthly():
    assert calc.fire_4pct_annual(1200) == 48
    assert calc.fire_4pct_monthly(1200) == 4


def test_fire_3pct_annual_and_monthly():
    assert calc.fire_3pct_annual(1200) == 36
    assert calc.fire_3pct_monthly(1200) == 3
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/Scripts/pytest tests/test_calc.py -v
```

Expected: `ModuleNotFoundError: No module named 'depositcalc.calc'` (or `ImportError`).

- [ ] **Step 3: Write `src/depositcalc/calc.py`**

```python
"""Pure financial formulas — a direct port of the Excel workbook's columns J-S.

No UI or storage dependencies here: this module is testable on desktop and
is the single source of truth for every derived number the app shows.
"""
from datetime import date


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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/Scripts/pytest tests/test_calc.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/depositcalc/calc.py tests/test_calc.py
git commit -m "Add core financial formulas ported from the Excel workbook"
```

---

### Task 3: Deposit model and per-deposit metrics aggregation

**Files:**
- Create: `src/depositcalc/models.py`
- Modify: `src/depositcalc/calc.py` (append `DepositMetrics` and `compute_metrics`)
- Modify: `tests/test_calc.py` (append aggregation tests)

**Interfaces:**
- Consumes: all functions from Task 2's `calc.py`.
- Produces (consumed by Task 4's `storage.py` and every Task 6-10 UI module):
  - `models.Deposit` dataclass: fields `bank: str`, `date_from: date`, `date_to: date`, `amount: float`, `rate: float`, `term_days: int`, `inflation: float`, `id: int | None = None`
  - `calc.DepositMetrics` dataclass: fields `promised_income`, `nominal_total`, `nominal_growth`, `nominal_yield`, `inflation_growth`, `inflation_over_term`, `real_yield`, `real_income_total`, `real_income_per_day`, `portfolio_share`, `days_to_close`, `fire_4pct_annual`, `fire_4pct_monthly`, `fire_3pct_annual`, `fire_3pct_monthly` (all `float` except `days_to_close: int`)
  - `calc.compute_metrics(deposit: Deposit, portfolio_total: float, today: date | None = None) -> DepositMetrics`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_calc.py`:

```python
from depositcalc.models import Deposit


def _sample_deposit(**overrides):
    defaults = dict(
        bank="Яндекс",
        date_from=date(2026, 1, 1),
        date_to=date(2026, 1, 31),
        amount=100,
        rate=0.13,
        term_days=30,
        inflation=0.09,
    )
    defaults.update(overrides)
    return Deposit(**defaults)


def test_compute_metrics_matches_individual_formulas():
    deposit = _sample_deposit()
    today = date(2026, 1, 1)
    metrics = calc.compute_metrics(deposit, portfolio_total=200, today=today)
    assert metrics.promised_income == pytest.approx(calc.promised_income(100, 0.13, 30))
    assert metrics.real_income_total == pytest.approx(0.296658, abs=1e-4)
    assert metrics.portfolio_share == pytest.approx(0.5)
    assert metrics.days_to_close == 30


def test_compute_metrics_empty_portfolio_share_is_zero():
    deposit = _sample_deposit()
    metrics = calc.compute_metrics(deposit, portfolio_total=0, today=date(2026, 1, 1))
    assert metrics.portfolio_share == 0.0


def test_compute_metrics_includes_fire_numbers():
    deposit = _sample_deposit(amount=1200)
    metrics = calc.compute_metrics(deposit, portfolio_total=1200, today=date(2026, 1, 1))
    assert metrics.fire_4pct_annual == 48
    assert metrics.fire_4pct_monthly == 4
    assert metrics.fire_3pct_annual == 36
    assert metrics.fire_3pct_monthly == 3
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/Scripts/pytest tests/test_calc.py -v
```

Expected: `ModuleNotFoundError: No module named 'depositcalc.models'`.

- [ ] **Step 3: Write `src/depositcalc/models.py`**

```python
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
```

- [ ] **Step 4: Append `DepositMetrics` and `compute_metrics` to `src/depositcalc/calc.py`**

Add these imports at the very top of the file, alongside the existing `from datetime import date`:

```python
from dataclasses import dataclass

from depositcalc.models import Deposit
```

Then append at the end of the file:

```python
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
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
.venv/Scripts/pytest tests/test_calc.py -v
```

Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add src/depositcalc/models.py src/depositcalc/calc.py tests/test_calc.py
git commit -m "Add Deposit model and per-deposit metrics aggregation"
```

---

### Task 4: SQLite storage layer

**Files:**
- Create: `src/depositcalc/storage.py`
- Create: `tests/test_storage.py`

**Interfaces:**
- Consumes: `models.Deposit` from Task 3.
- Produces (consumed by Task 10's `main.py`):
  - `connect(db_path: str) -> sqlite3.Connection` (creates the `deposits` table if missing)
  - `add_deposit(conn, deposit: Deposit) -> int` (returns the new row id)
  - `get_all_deposits(conn) -> list[Deposit]`
  - `get_deposit(conn, deposit_id: int) -> Deposit | None`
  - `update_deposit(conn, deposit: Deposit) -> None` (requires `deposit.id` to be set)
  - `delete_deposit(conn, deposit_id: int) -> None`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_storage.py
import pytest
from datetime import date

from depositcalc import storage
from depositcalc.models import Deposit


def _sample_deposit(**overrides):
    defaults = dict(
        bank="Тинькофф",
        date_from=date(2026, 1, 1),
        date_to=date(2026, 2, 1),
        amount=500.0,
        rate=0.15,
        term_days=31,
        inflation=0.08,
    )
    defaults.update(overrides)
    return Deposit(**defaults)


def test_add_deposit_returns_generated_id(tmp_path):
    conn = storage.connect(str(tmp_path / "deposits.db"))
    deposit_id = storage.add_deposit(conn, _sample_deposit())
    assert deposit_id == 1


def test_get_all_deposits_returns_added_deposits_in_order(tmp_path):
    conn = storage.connect(str(tmp_path / "deposits.db"))
    storage.add_deposit(conn, _sample_deposit(bank="Тинькофф"))
    storage.add_deposit(conn, _sample_deposit(bank="Сбер"))
    deposits = storage.get_all_deposits(conn)
    assert [d.bank for d in deposits] == ["Тинькофф", "Сбер"]


def test_get_deposit_returns_none_for_missing_id(tmp_path):
    conn = storage.connect(str(tmp_path / "deposits.db"))
    assert storage.get_deposit(conn, 999) is None


def test_get_deposit_returns_matching_fields(tmp_path):
    conn = storage.connect(str(tmp_path / "deposits.db"))
    deposit_id = storage.add_deposit(conn, _sample_deposit(amount=750.0))
    fetched = storage.get_deposit(conn, deposit_id)
    assert fetched.amount == 750.0
    assert fetched.date_from == date(2026, 1, 1)
    assert fetched.id == deposit_id


def test_update_deposit_persists_changes(tmp_path):
    conn = storage.connect(str(tmp_path / "deposits.db"))
    deposit_id = storage.add_deposit(conn, _sample_deposit(amount=500.0))
    updated = _sample_deposit(id=deposit_id, amount=750.0)
    storage.update_deposit(conn, updated)
    fetched = storage.get_deposit(conn, deposit_id)
    assert fetched.amount == 750.0


def test_update_deposit_without_id_raises_value_error(tmp_path):
    conn = storage.connect(str(tmp_path / "deposits.db"))
    with pytest.raises(ValueError):
        storage.update_deposit(conn, _sample_deposit())


def test_delete_deposit_removes_it(tmp_path):
    conn = storage.connect(str(tmp_path / "deposits.db"))
    deposit_id = storage.add_deposit(conn, _sample_deposit())
    storage.delete_deposit(conn, deposit_id)
    assert storage.get_deposit(conn, deposit_id) is None


def test_deposits_persist_across_reconnect(tmp_path):
    db_path = str(tmp_path / "deposits.db")
    conn = storage.connect(db_path)
    storage.add_deposit(conn, _sample_deposit())
    conn.close()

    reconnected = storage.connect(db_path)
    deposits = storage.get_all_deposits(reconnected)
    assert len(deposits) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/Scripts/pytest tests/test_storage.py -v
```

Expected: `ModuleNotFoundError: No module named 'depositcalc.storage'`.

- [ ] **Step 3: Write `src/depositcalc/storage.py`**

```python
"""SQLite persistence for deposits — no UI dependencies."""
import sqlite3
from datetime import date

from depositcalc.models import Deposit

_SCHEMA = """
CREATE TABLE IF NOT EXISTS deposits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bank TEXT NOT NULL,
    date_from TEXT NOT NULL,
    date_to TEXT NOT NULL,
    amount REAL NOT NULL,
    rate REAL NOT NULL,
    term_days INTEGER NOT NULL,
    inflation REAL NOT NULL
)
"""


def connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute(_SCHEMA)
    conn.commit()
    return conn


def _row_to_deposit(row: sqlite3.Row) -> Deposit:
    return Deposit(
        id=row["id"],
        bank=row["bank"],
        date_from=date.fromisoformat(row["date_from"]),
        date_to=date.fromisoformat(row["date_to"]),
        amount=row["amount"],
        rate=row["rate"],
        term_days=row["term_days"],
        inflation=row["inflation"],
    )


def add_deposit(conn: sqlite3.Connection, deposit: Deposit) -> int:
    cursor = conn.execute(
        "INSERT INTO deposits (bank, date_from, date_to, amount, rate, term_days, inflation) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            deposit.bank,
            deposit.date_from.isoformat(),
            deposit.date_to.isoformat(),
            deposit.amount,
            deposit.rate,
            deposit.term_days,
            deposit.inflation,
        ),
    )
    conn.commit()
    return cursor.lastrowid


def get_all_deposits(conn: sqlite3.Connection) -> list[Deposit]:
    rows = conn.execute("SELECT * FROM deposits ORDER BY id").fetchall()
    return [_row_to_deposit(row) for row in rows]


def get_deposit(conn: sqlite3.Connection, deposit_id: int) -> Deposit | None:
    row = conn.execute("SELECT * FROM deposits WHERE id = ?", (deposit_id,)).fetchone()
    return _row_to_deposit(row) if row else None


def update_deposit(conn: sqlite3.Connection, deposit: Deposit) -> None:
    if deposit.id is None:
        raise ValueError("Cannot update a deposit without an id")
    conn.execute(
        "UPDATE deposits SET bank = ?, date_from = ?, date_to = ?, amount = ?, "
        "rate = ?, term_days = ?, inflation = ? WHERE id = ?",
        (
            deposit.bank,
            deposit.date_from.isoformat(),
            deposit.date_to.isoformat(),
            deposit.amount,
            deposit.rate,
            deposit.term_days,
            deposit.inflation,
            deposit.id,
        ),
    )
    conn.commit()


def delete_deposit(conn: sqlite3.Connection, deposit_id: int) -> None:
    conn.execute("DELETE FROM deposits WHERE id = ?", (deposit_id,))
    conn.commit()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/Scripts/pytest tests/test_storage.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/depositcalc/storage.py tests/test_storage.py
git commit -m "Add SQLite storage layer for deposits"
```

---

### Task 5: Bank gradient color palette

**Files:**
- Create: `src/depositcalc/ui/colors.py`
- Create: `tests/test_colors.py`

**Interfaces:**
- Consumes: nothing.
- Produces (consumed by Task 6's `widgets.py` builders and Task 7/9 screens):
  - `colors.PALETTE: list[tuple[str, str]]` (hex `(start, end)` pairs)
  - `colors.bank_gradient(bank: str) -> tuple[str, str]`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_colors.py
from depositcalc.ui.colors import PALETTE, bank_gradient


def test_bank_gradient_is_deterministic_for_same_name():
    assert bank_gradient("Тинькофф") == bank_gradient("Тинькофф")


def test_bank_gradient_is_from_palette():
    assert bank_gradient("Сбер") in PALETTE


def test_bank_gradient_returns_two_distinct_colors():
    start, end = bank_gradient("Яндекс")
    assert start != end


def test_different_banks_can_get_different_gradients():
    names = ["Тинькофф", "Сбер", "Альфа", "ВТБ", "Яндекс", "Газпромбанк", "Открытие", "Совкомбанк"]
    gradients = {bank_gradient(name) for name in names}
    assert len(gradients) > 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/Scripts/pytest tests/test_colors.py -v
```

Expected: `ModuleNotFoundError: No module named 'depositcalc.ui.colors'`.

- [ ] **Step 3: Write `src/depositcalc/ui/colors.py`**

Python's built-in `hash()` on strings is randomized per process (`PYTHONHASHSEED`), so it must not be used here — the same bank has to map to the same card gradient every time the app restarts. `zlib.crc32` is deterministic and well-distributed. Each palette entry is a `(start, end)` hex pair for the diagonal gradient described in spec §6.2 ("мягкий линейный градиент из двух пастельных оттенков").

```python
"""Deterministic pastel gradient pair per bank name, for portfolio cards and the detail hero."""
import zlib

PALETTE: list[tuple[str, str]] = [
    ("#DCE8FF", "#EAF1FF"),  # periwinkle -> pale blue
    ("#FFE8CC", "#FFF3E0"),  # peach -> pale orange
    ("#D9F2D9", "#EAF7E5"),  # mint -> pale green
    ("#FFE0EC", "#FFEEF3"),  # pink -> pale pink
    ("#E8DFFF", "#F1EBFF"),  # lavender -> pale violet
    ("#FFF6CC", "#FFFBE0"),  # butter -> pale yellow
    ("#D6F5F0", "#E9FAF7"),  # aqua -> pale teal
    ("#F0E0D6", "#F8EFE9"),  # sand -> pale beige
]


def bank_gradient(bank: str) -> tuple[str, str]:
    """Same bank name always maps to the same palette gradient, across process restarts."""
    digest = zlib.crc32(bank.encode("utf-8"))
    return PALETTE[digest % len(PALETTE)]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/Scripts/pytest tests/test_colors.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/depositcalc/ui/colors.py tests/test_colors.py
git commit -m "Add deterministic bank gradient palette"
```

---

### Task 6: Shared Kivy canvas widgets

**Files:**
- Create: `src/depositcalc/ui/widgets.py`

**Interfaces:**
- Consumes: nothing (pure Kivy graphics helpers, no app logic).
- Produces (consumed by Task 7's `portfolio_screen.py` and Task 9's `deposit_detail_screen.py`):
  - `GradientCard(ButtonBehavior, BoxLayout)` — `GradientCard(start_hex: str, end_hex: str, radius: int = 24, **kwargs)`; fires the standard Kivy `on_release` event on tap anywhere inside it (including over its children, since `Label`s don't consume touch).
  - `DashedPlaceholderCard(ButtonBehavior, BoxLayout)` — `DashedPlaceholderCard(radius: int = 24, **kwargs)`; same tap behavior.
  - `Badge(Widget)` — `Badge(text: str, pad_x: int = 12, pad_y: int = 4, **kwargs)`; a pill-shaped translucent-white badge that self-sizes to its text.
  - `left_label(text: str, **kwargs) -> Label` — a `Label` factory that wires `text_size` to the label's own size so `halign="left"` (the default) actually renders left-aligned instead of being silently centered (see Global Constraints).

No automated tests for this task — pure canvas/visual code, per spec §8 the UI layer is verified manually. A non-visual smoke check (Step 2) catches import/construction errors before Task 7/9 build on top of it.

- [ ] **Step 1: Write `src/depositcalc/ui/widgets.py`**

```python
"""Reusable Kivy canvas widgets: gradient cards, dashed placeholder, badge pill,
and a Label factory that makes `halign` actually work.

Kivy widgets don't draw backgrounds on their own — anything with a rounded
rect, gradient, or dashed border here manually keeps a canvas shape in sync
with the widget's `pos`/`size` via `bind()`. Centralizing that once here means
screen-building code (Task 7, Task 9) never has to touch `canvas` directly.
"""
from kivy.graphics import Color, Line, RoundedRectangle
from kivy.graphics.texture import Texture
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget


def _hex_to_rgba(hex_color: str) -> tuple[float, float, float, float]:
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16) / 255
    g = int(hex_color[2:4], 16) / 255
    b = int(hex_color[4:6], 16) / 255
    return (r, g, b, 1.0)


def _make_gradient_texture(start_hex: str, end_hex: str) -> Texture:
    """2x2 bilinear-filtered texture: stretched over a rect it reads as a
    smooth diagonal gradient running from `start_hex` (bottom-left) to
    `end_hex` (top-right), with the anti-diagonal corners averaged."""
    start = _hex_to_rgba(start_hex)
    end = _hex_to_rgba(end_hex)
    mid = tuple((s + e) / 2 for s, e in zip(start, end))

    def to_bytes(rgba):
        return bytes(int(round(c * 255)) for c in rgba)

    bottom_row = to_bytes(start) + to_bytes(mid)
    top_row = to_bytes(mid) + to_bytes(end)

    texture = Texture.create(size=(2, 2), colorfmt="rgba")
    texture.mag_filter = "linear"
    texture.min_filter = "linear"
    texture.blit_buffer(bottom_row + top_row, colorfmt="rgba", bufferfmt="ubyte")
    return texture


class GradientCard(ButtonBehavior, BoxLayout):
    """A rounded box with a diagonal two-color gradient background, tappable as a whole."""

    def __init__(self, start_hex: str, end_hex: str, radius: int = 24, **kwargs):
        super().__init__(**kwargs)
        self._radius = radius
        self._texture = _make_gradient_texture(start_hex, end_hex)
        with self.canvas.before:
            Color(1, 1, 1, 1)
            self._rect = RoundedRectangle(
                pos=self.pos, size=self.size, radius=[self._radius], texture=self._texture
            )
        self.bind(pos=self._sync_rect, size=self._sync_rect)

    def _sync_rect(self, *_args):
        self._rect.pos = self.pos
        self._rect.size = self.size


class DashedPlaceholderCard(ButtonBehavior, BoxLayout):
    """The '+ Добавить вклад' card: light gray fill, dashed rounded border."""

    def __init__(self, radius: int = 24, **kwargs):
        super().__init__(**kwargs)
        self._radius = radius
        with self.canvas.before:
            Color(0.94, 0.94, 0.94, 1)
            self._fill = RoundedRectangle(pos=self.pos, size=self.size, radius=[self._radius])
            Color(0.75, 0.75, 0.75, 1)
            self._border = Line(
                rounded_rectangle=(self.x, self.y, self.width, self.height, self._radius),
                dash_length=6,
                dash_offset=4,
                width=1.2,
            )
        self.bind(pos=self._sync_shapes, size=self._sync_shapes)

    def _sync_shapes(self, *_args):
        self._fill.pos = self.pos
        self._fill.size = self.size
        self._border.rounded_rectangle = (self.x, self.y, self.width, self.height, self._radius)


class Badge(Widget):
    """A pill-shaped, semi-transparent-white badge that sizes itself to its text."""

    def __init__(self, text: str, pad_x: int = 12, pad_y: int = 4, **kwargs):
        kwargs.setdefault("size_hint", (None, None))
        super().__init__(**kwargs)
        self._pad_x, self._pad_y = pad_x, pad_y
        self._label = Label(
            text=text, size_hint=(None, None), bold=True, font_size=13, color=(0.15, 0.15, 0.15, 1)
        )
        self._label.bind(texture_size=self._on_label_size)
        self.add_widget(self._label)
        with self.canvas.before:
            Color(1, 1, 1, 0.55)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[12])
        self.bind(pos=self._sync, size=self._sync)

    def _on_label_size(self, _label, texture_size):
        self._label.size = texture_size
        self.width = texture_size[0] + self._pad_x * 2
        self.height = texture_size[1] + self._pad_y * 2
        self._label.center = self.center

    def _sync(self, *_args):
        self._rect.pos = self.pos
        self._rect.size = self.size
        self._rect.radius = [self.height / 2]
        self._label.center = self.center


def left_label(text: str, **kwargs) -> Label:
    """A Label whose `halign`/`valign` actually take effect (Kivy ignores
    both unless `text_size` tracks the widget's own size)."""
    kwargs.setdefault("halign", "left")
    kwargs.setdefault("valign", "middle")
    label = Label(text=text, **kwargs)
    label.bind(size=lambda inst, size: setattr(inst, "text_size", size))
    return label
```

- [ ] **Step 2: Manually verify the widgets import and construct without error**

```bash
.venv/Scripts/python -c "
from depositcalc.ui.widgets import GradientCard, DashedPlaceholderCard, Badge, left_label

card = GradientCard('#DCE8FF', '#EAF1FF', size_hint=(None, None), size=(150, 150))
placeholder = DashedPlaceholderCard(size_hint=(None, None), size=(300, 64))
badge = Badge('+1 068 ₽')
label = left_label('Яндекс, 30 дней')
print(type(card), type(placeholder), type(badge), type(label))
"
```

Expected: prints the four class types with no traceback.

- [ ] **Step 3: Commit**

```bash
git add src/depositcalc/ui/widgets.py
git commit -m "Add shared Kivy gradient/dashed/badge canvas widgets"
```

---

### Task 7: Portfolio screen (card grid)

**Files:**
- Create: `src/depositcalc/ui/portfolio_screen.py`

**Interfaces:**
- Consumes: `calc.compute_metrics`, `calc.DepositMetrics` (Task 3), `models.Deposit` (Task 3), `colors.bank_gradient` (Task 5), `widgets.GradientCard`/`DashedPlaceholderCard`/`Badge`/`left_label` (Task 6).
- Produces (consumed by Task 10's `main.py`):
  - `PortfolioScreen(Screen)` with `.update(deposits: list[Deposit], on_tap_deposit: Callable[[int], None], on_add: Callable[[], None]) -> None`

No automated tests for this task — per spec §8 the UI layer is verified manually. Matches `01 Портфель.png`: header (title, "Всего в портфеле" caption, total), 2-column card grid (bank+term, one promised-income badge, large `amount`, "ставка · доля" caption), dashed "+ Добавить вклад" card below the grid.

- [ ] **Step 1: Write `src/depositcalc/ui/portfolio_screen.py`**

```python
"""Portfolio screen: header totals + 2-column deposit card grid + add card.

Matches docs/superpowers/design/01 Портфель.png exactly — see spec §6.2.
"""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import Screen

from depositcalc import calc
from depositcalc.models import Deposit
from depositcalc.ui.colors import bank_gradient
from depositcalc.ui.widgets import Badge, DashedPlaceholderCard, GradientCard, left_label


def _format_money(value: float) -> str:
    return f"{value:,.0f} ₽".replace(",", " ")


def _build_card(deposit: Deposit, metrics: calc.DepositMetrics, on_tap) -> GradientCard:
    start, end = bank_gradient(deposit.bank)
    card = GradientCard(
        start, end,
        orientation="vertical", padding=16, spacing=6,
        size_hint=(1, None), height=170,
    )
    card.add_widget(left_label(
        f"{deposit.bank}, {deposit.term_days} дней",
        bold=True, color=(0.1, 0.1, 0.1, 1), size_hint_y=None, height=24,
    ))
    badge_row = BoxLayout(size_hint_y=None, height=28)
    badge_row.add_widget(Badge(f"+{_format_money(metrics.promised_income)}"))
    badge_row.add_widget(Label())  # spacer so the badge doesn't stretch to full width
    card.add_widget(badge_row)
    card.add_widget(left_label(
        _format_money(deposit.amount),
        bold=True, font_size=24, color=(0.05, 0.05, 0.05, 1), size_hint_y=None, height=32,
    ))
    card.add_widget(left_label(
        f"{deposit.rate:.0%} · доля {metrics.portfolio_share:.0%}",
        font_size=12, color=(0.35, 0.35, 0.35, 1), size_hint_y=None, height=18,
    ))
    card.bind(on_release=lambda *_args: on_tap(deposit.id))
    return card


def _build_placeholder(on_add) -> DashedPlaceholderCard:
    card = DashedPlaceholderCard(size_hint=(1, None), height=64)
    card.add_widget(Label(text="+ Добавить вклад", color=(0.4, 0.4, 0.4, 1)))
    card.bind(on_release=lambda *_args: on_add())
    return card


def build_portfolio_content(deposits: list[Deposit], on_tap_deposit, on_add) -> ScrollView:
    total_amount = sum(d.amount for d in deposits)

    header = BoxLayout(orientation="vertical", size_hint_y=None, height=110, padding=(16, 12))
    header.add_widget(Label(
        text="Мои вклады", bold=True, font_size=20, color=(0.1, 0.1, 0.1, 1),
        size_hint_y=None, height=28,
    ))
    header.add_widget(left_label(
        "Всего в портфеле", font_size=12, color=(0.5, 0.5, 0.5, 1), size_hint_y=None, height=18,
    ))
    header.add_widget(left_label(
        _format_money(total_amount), bold=True, font_size=22, color=(0.05, 0.05, 0.05, 1),
        size_hint_y=None, height=32,
    ))

    grid = GridLayout(cols=2, spacing=12, padding=12, size_hint_y=None)
    grid.bind(minimum_height=grid.setter("height"))
    for deposit in deposits:
        metrics = calc.compute_metrics(deposit, total_amount)
        grid.add_widget(_build_card(deposit, metrics, on_tap_deposit))

    content = BoxLayout(orientation="vertical", size_hint_y=None, spacing=8, padding=(0, 0, 0, 16))
    content.bind(minimum_height=content.setter("height"))
    content.add_widget(header)
    content.add_widget(grid)
    content.add_widget(_build_placeholder(on_add))

    scroll = ScrollView()
    scroll.add_widget(content)
    return scroll


class PortfolioScreen(Screen):
    def update(self, deposits, on_tap_deposit, on_add):
        self.clear_widgets()
        self.add_widget(build_portfolio_content(deposits, on_tap_deposit, on_add))
```

- [ ] **Step 2: Manually verify the screen builds without error**

```bash
.venv/Scripts/python -c "
from datetime import date
from depositcalc.models import Deposit
from depositcalc.ui.portfolio_screen import PortfolioScreen

deposits = [
    Deposit(bank='Яндекс', date_from=date(2026,1,1), date_to=date(2026,1,31), amount=100000, rate=0.13, term_days=30, inflation=0.09, id=1),
    Deposit(bank='Т-Банк', date_from=date(2026,1,1), date_to=date(2026,4,1), amount=45000, rate=0.15, term_days=90, inflation=0.09, id=2),
]
screen = PortfolioScreen(name='portfolio')
screen.update(deposits, on_tap_deposit=lambda i: None, on_add=lambda: None)
print(type(screen), len(screen.children))
"
```

Expected: prints the screen type and a nonzero child count, no traceback. This only checks the widget tree builds; visual details (gradient colors, badge, grid layout, tapping) are only visible once `main.py` puts this screen in a real running window (Task 10).

- [ ] **Step 3: Commit**

```bash
git add src/depositcalc/ui/portfolio_screen.py
git commit -m "Add portfolio screen card grid"
```

---

### Task 8: Deposit form (add/edit)

**Files:**
- Create: `src/depositcalc/ui/deposit_form_screen.py`

**Interfaces:**
- Consumes: `models.Deposit` (Task 3), `widgets.left_label` (Task 6).
- Produces (consumed by Task 10's `main.py`):
  - `DepositFormScreen(Screen)` with `.show(on_save: Callable[[Deposit], None], on_cancel: Callable[[], None], deposit: Deposit | None = None) -> None` — `deposit=None` means "add" mode; otherwise "edit" mode (pre-fills fields, preserves `deposit.id`).

No automated tests for this task — per spec §8 the UI layer is verified manually. No mockup exists for this screen (spec §6.4); it's built from the prose description: rounded light-gray inputs with a label above each, one accent "Сохранить" button, plain-text "Отмена".

- [ ] **Step 1: Write `src/depositcalc/ui/deposit_form_screen.py`**

Per spec §5, `date_to` earlier than `date_from` is a **soft warning, not a blocker** ("в Excel сам файл такого ограничения не имеет") — the form still saves the deposit but shows a warning message. Amount/term_days/rate/inflation validation, plus a basic date-format check (Kivy has no built-in date picker, so dates are typed as `ГГГГ-ММ-ДД` text), all block saving.

```python
"""Reusable add/edit form screen for a single deposit — no mockup, see spec §6.4."""
from datetime import date

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.textinput import TextInput

from depositcalc.models import Deposit
from depositcalc.ui.widgets import left_label


def _labeled_input(label_text: str, initial: str, input_filter=None) -> tuple[BoxLayout, TextInput]:
    row = BoxLayout(orientation="vertical", size_hint_y=None, height=64, spacing=2)
    row.add_widget(left_label(label_text, font_size=12, color=(0.45, 0.45, 0.45, 1), size_hint_y=None, height=18))
    text_input = TextInput(
        text=initial, multiline=False, input_filter=input_filter,
        size_hint_y=None, height=40, background_color=(0.95, 0.95, 0.95, 1),
    )
    row.add_widget(text_input)
    return row, text_input


class DepositFormScreen(Screen):
    def show(self, on_save, on_cancel, deposit: Deposit | None = None):
        self.clear_widgets()
        self._on_save = on_save
        self._on_cancel = on_cancel
        self._deposit_id = deposit.id if deposit else None

        bank_row, self._bank_input = _labeled_input("Банк", deposit.bank if deposit else "")
        date_from_row, self._date_from_input = _labeled_input(
            "Дата открытия (ГГГГ-ММ-ДД)", deposit.date_from.isoformat() if deposit else date.today().isoformat()
        )
        date_to_row, self._date_to_input = _labeled_input(
            "Дата закрытия (ГГГГ-ММ-ДД)", deposit.date_to.isoformat() if deposit else date.today().isoformat()
        )
        amount_row, self._amount_input = _labeled_input(
            "Сумма, ₽", str(deposit.amount) if deposit else "", input_filter="float"
        )
        rate_row, self._rate_input = _labeled_input(
            "Ставка (доля, напр. 0.13 = 13%)", str(deposit.rate) if deposit else "", input_filter="float"
        )
        term_days_row, self._term_days_input = _labeled_input(
            "Срок, дней", str(deposit.term_days) if deposit else "", input_filter="int"
        )
        inflation_row, self._inflation_input = _labeled_input(
            "Инфляция (доля, напр. 0.09 = 9%)", str(deposit.inflation) if deposit else "", input_filter="float"
        )

        self._message_label = Label(text="", color=(0.8, 0.1, 0.1, 1), size_hint_y=None, height=24)

        buttons_row = BoxLayout(size_hint_y=None, height=48, spacing=8)
        cancel_button = Button(text="Отмена", background_color=(0, 0, 0, 0), color=(0.3, 0.3, 0.3, 1))
        cancel_button.bind(on_release=lambda *_args: self._on_cancel())
        save_button = Button(text="Сохранить", background_normal="", background_color=(0.35, 0.55, 1, 1))
        save_button.bind(on_release=lambda *_args: self._handle_save())
        buttons_row.add_widget(cancel_button)
        buttons_row.add_widget(save_button)

        form = BoxLayout(orientation="vertical", padding=16, spacing=8, size_hint_y=None)
        form.bind(minimum_height=form.setter("height"))
        for row in (
            bank_row, date_from_row, date_to_row, amount_row,
            rate_row, term_days_row, inflation_row,
        ):
            form.add_widget(row)
        form.add_widget(self._message_label)
        form.add_widget(buttons_row)

        self.add_widget(form)

    def _blocking_error(self) -> str | None:
        if not self._bank_input.text.strip():
            return "Укажите название банка"
        try:
            date.fromisoformat(self._date_from_input.text.strip())
            date.fromisoformat(self._date_to_input.text.strip())
        except ValueError:
            return "Некорректная дата, используйте формат ГГГГ-ММ-ДД"
        try:
            amount = float(self._amount_input.text)
        except ValueError:
            amount = 0
        if amount <= 0:
            return "Сумма должна быть больше нуля"
        try:
            term_days = int(self._term_days_input.text)
        except ValueError:
            term_days = 0
        if term_days <= 0:
            return "Срок должен быть больше нуля"
        try:
            rate = float(self._rate_input.text)
        except ValueError:
            rate = -1
        if rate < 0:
            return "Ставка не может быть отрицательной"
        try:
            inflation = float(self._inflation_input.text)
        except ValueError:
            inflation = -1
        if inflation < 0:
            return "Инфляция не может быть отрицательной"
        return None

    def _handle_save(self):
        error = self._blocking_error()
        if error:
            self._message_label.text = error
            return

        date_from = date.fromisoformat(self._date_from_input.text.strip())
        date_to = date.fromisoformat(self._date_to_input.text.strip())
        if date_to < date_from:
            self._message_label.text = "Внимание: дата закрытия раньше даты открытия"
        else:
            self._message_label.text = ""

        deposit = Deposit(
            id=self._deposit_id,
            bank=self._bank_input.text.strip(),
            date_from=date_from,
            date_to=date_to,
            amount=float(self._amount_input.text),
            rate=float(self._rate_input.text),
            term_days=int(self._term_days_input.text),
            inflation=float(self._inflation_input.text),
        )
        self._on_save(deposit)
```

- [ ] **Step 2: Manually verify the screen builds without error**

```bash
.venv/Scripts/python -c "
from depositcalc.ui.deposit_form_screen import DepositFormScreen

screen = DepositFormScreen(name='form')
screen.show(on_save=lambda d: print('saved', d), on_cancel=lambda: print('cancelled'))
print(type(screen), len(screen.children))
"
```

Expected: prints the screen type and a nonzero child count, no traceback. This only checks the widget tree builds; interactive behavior (typing values, validation messages, save/cancel) is only visible once `main.py` puts this screen in a real running window (Task 10).

- [ ] **Step 3: Commit**

```bash
git add src/depositcalc/ui/deposit_form_screen.py
git commit -m "Add reusable deposit add/edit form screen"
```

---

### Task 9: Deposit detail screen (hero + grouped fields + FIRE)

**Files:**
- Create: `src/depositcalc/ui/deposit_detail_screen.py`

**Interfaces:**
- Consumes: `calc.compute_metrics`, `calc.DepositMetrics` (Task 3), `models.Deposit` (Task 3), `colors.bank_gradient` (Task 5), `widgets.GradientCard`/`Badge`/`left_label` (Task 6).
- Produces (consumed by Task 10's `main.py`):
  - `DepositDetailScreen(Screen)` with `.update(deposit: Deposit, portfolio_total: float, on_back: Callable[[], None], on_edit: Callable[[], None], on_delete: Callable[[], None]) -> None`

No automated tests for this task — per spec §8 the UI layer is verified manually. Matches `Калькулятор вкладов — дизайн.png` (right frame) exactly: header (← Назад / Изменить / Удалить), hero (gradient, two badges — Обещ. and Реальн. — plus large `amount`), "✎ Вы вводите" section (tappable field rows on a light gray background), "🧮 Рассчитывается автоматически" section (three subsections), "🔥 FIRE" section (two side-by-side columns).

Design note: spec §6.3 describes each "Вы вводите" row as tappable "to edit that field", but §6.4 describes only one reusable whole-record form, with no per-field editor anywhere in the spec. Building a second, per-field editing UI would contradict that reuse and isn't specified anywhere, so every field row's tap routes to the same whole-record edit form as the header's "Изменить" button — consistent with the spec's own reusable-form design, while still giving the `›` affordance the mockup shows.

- [ ] **Step 1: Write `src/depositcalc/ui/deposit_detail_screen.py`**

```python
"""Deposit detail screen: hero card, input/computed grouping, FIRE section.

Matches docs/superpowers/design/Калькулятор вкладов — дизайн.png (right
frame) exactly — see spec §6.3.
"""
from kivy.graphics import Color, Rectangle
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import Screen

from depositcalc import calc
from depositcalc.models import Deposit
from depositcalc.ui.colors import bank_gradient
from depositcalc.ui.widgets import Badge, GradientCard, left_label


def _format_money(value: float) -> str:
    return f"{value:,.1f} ₽".replace(",", " ")


def _build_header(on_back, on_edit, on_delete) -> BoxLayout:
    row = BoxLayout(size_hint_y=None, height=48, padding=(8, 4))
    back_button = Button(text="← Назад", background_color=(0, 0, 0, 0), color=(0.2, 0.2, 0.2, 1))
    back_button.bind(on_release=lambda *_args: on_back())
    edit_button = Button(text="Изменить", background_color=(0, 0, 0, 0), color=(0.2, 0.2, 0.2, 1))
    edit_button.bind(on_release=lambda *_args: on_edit())
    delete_button = Button(text="Удалить", background_color=(0, 0, 0, 0), color=(0.8, 0.15, 0.15, 1))
    delete_button.bind(on_release=lambda *_args: on_delete())
    row.add_widget(back_button)
    row.add_widget(edit_button)
    row.add_widget(delete_button)
    return row


def _build_hero(deposit: Deposit, metrics: calc.DepositMetrics) -> GradientCard:
    start, end = bank_gradient(deposit.bank)
    hero = GradientCard(start, end, orientation="vertical", padding=16, spacing=8, size_hint_y=None, height=160)
    hero.add_widget(left_label(
        f"{deposit.bank}, {deposit.term_days} дней",
        bold=True, font_size=16, color=(0.1, 0.1, 0.1, 1), size_hint_y=None, height=24,
    ))
    badge_row = BoxLayout(size_hint_y=None, height=28, spacing=8)
    badge_row.add_widget(Badge(f"Обещ.: +{_format_money(metrics.promised_income)}"))
    badge_row.add_widget(Badge(f"Реальн.: +{_format_money(metrics.real_income_total)}"))
    badge_row.add_widget(Label())  # spacer, keeps badges from stretching to full width
    hero.add_widget(badge_row)
    hero.add_widget(left_label(
        _format_money(deposit.amount),
        bold=True, font_size=28, color=(0.05, 0.05, 0.05, 1), size_hint_y=None, height=40,
    ))
    return hero


class _FieldRow(ButtonBehavior, BoxLayout):
    """A tappable 'label ... value \u203a' row for the '\u0412\u044b \u0432\u0432\u043e\u0434\u0438\u0442\u0435' section.

    Two left_label()s (one left-aligned, one right-aligned) rather than a
    single Button \u2014 Kivy Buttons have the same halign-needs-text_size
    limitation as Label, and cramming both pieces of text into one string
    can't align a label to the left and a value to the right independently.
    """


def _field_row(label: str, value: str, on_edit) -> _FieldRow:
    row = _FieldRow(size_hint_y=None, height=44, padding=(4, 0))
    row.add_widget(left_label(label, color=(0.15, 0.15, 0.15, 1)))
    row.add_widget(left_label(f"{value}  \u203a", halign="right", color=(0.15, 0.15, 0.15, 1)))
    row.bind(on_release=lambda *_args: on_edit())
    return row


def _build_input_section(deposit: Deposit, on_edit) -> BoxLayout:
    section = BoxLayout(orientation="vertical", size_hint_y=None, padding=(12, 8))
    section.bind(minimum_height=section.setter("height"))
    with section.canvas.before:
        Color(0.96, 0.96, 0.96, 1)
        rect = Rectangle(pos=section.pos, size=section.size)
    section.bind(pos=lambda inst, val: setattr(rect, "pos", val), size=lambda inst, val: setattr(rect, "size", val))

    section.add_widget(left_label(
        "\u270e Вы вводите", bold=True, color=(0.25, 0.45, 0.9, 1), size_hint_y=None, height=32,
    ))
    section.add_widget(_field_row("Банк", deposit.bank, on_edit))
    section.add_widget(_field_row("Дата открытия", deposit.date_from.isoformat(), on_edit))
    section.add_widget(_field_row("Дата закрытия", deposit.date_to.isoformat(), on_edit))
    section.add_widget(_field_row("Сумма", _format_money(deposit.amount), on_edit))
    section.add_widget(_field_row("Ставка", f"{deposit.rate:.0%}", on_edit))
    section.add_widget(_field_row("Срок", f"{deposit.term_days} дней", on_edit))
    section.add_widget(_field_row("Инфляция", f"{deposit.inflation:.0%}", on_edit))
    return section


def _computed_row(label: str, value: str) -> BoxLayout:
    row = BoxLayout(size_hint_y=None, height=28, padding=(12, 0))
    row.add_widget(left_label(label, color=(0.15, 0.15, 0.15, 1)))
    row.add_widget(left_label(value, halign="right", color=(0.15, 0.15, 0.15, 1)))
    return row


def _build_computed_section(metrics: calc.DepositMetrics) -> BoxLayout:
    section = BoxLayout(orientation="vertical", size_hint_y=None, padding=(0, 8))
    section.bind(minimum_height=section.setter("height"))

    def subheading(text: str) -> Label:
        return left_label(text, color=(0.55, 0.55, 0.55, 1), size_hint_y=None, height=28, font_size=12)

    section.add_widget(left_label(
        "\U0001f9ee Рассчитывается автоматически",
        bold=True, color=(0.55, 0.55, 0.55, 1), size_hint_y=None, height=32,
    ))
    section.add_widget(subheading("Номинальная доходность"))
    section.add_widget(_computed_row("Рост суммы", f"{metrics.nominal_growth:.4f}"))
    section.add_widget(_computed_row("Доходность", f"{metrics.nominal_yield:.2%}"))
    section.add_widget(subheading("Реальная доходность (с поправкой на инфляцию)"))
    section.add_widget(_computed_row("Рост инфляции за срок", f"{metrics.inflation_growth:.4f}"))
    section.add_widget(_computed_row("Инфляция за срок", f"{metrics.inflation_over_term:.2%}"))
    section.add_widget(_computed_row("Реальная доходность", f"{metrics.real_yield:.2%}"))
    section.add_widget(_computed_row("Реальный доход за срок", _format_money(metrics.real_income_total)))
    section.add_widget(_computed_row("Реальный доход в день", _format_money(metrics.real_income_per_day)))
    section.add_widget(subheading("Портфель"))
    section.add_widget(_computed_row("Доля в портфеле", f"{metrics.portfolio_share:.0%}"))
    section.add_widget(_computed_row("Дней до закрытия", str(metrics.days_to_close)))
    return section


def _build_fire_section(metrics: calc.DepositMetrics) -> BoxLayout:
    section = BoxLayout(orientation="vertical", size_hint_y=None, padding=(12, 8), spacing=4)
    section.bind(minimum_height=section.setter("height"))
    section.add_widget(left_label(
        "\U0001f525 FIRE", bold=True, color=(0.55, 0.55, 0.55, 1), size_hint_y=None, height=32,
    ))
    section.add_widget(left_label(
        "Правило безопасного снятия капитала на пенсии, без индексации на инфляцию",
        font_size=11, color=(0.55, 0.55, 0.55, 1), size_hint_y=None, height=32,
    ))

    columns = BoxLayout(size_hint_y=None, height=90, spacing=12)
    for title, annual, monthly in (
        ("Правило 4%", metrics.fire_4pct_annual, metrics.fire_4pct_monthly),
        ("Правило 3%", metrics.fire_3pct_annual, metrics.fire_3pct_monthly),
    ):
        column = BoxLayout(orientation="vertical")
        column.add_widget(left_label(title, bold=True, size_hint_y=None, height=24))
        column.add_widget(left_label(f"В год: {_format_money(annual)}", size_hint_y=None, height=22))
        column.add_widget(left_label(f"В месяц: {_format_money(monthly)}", size_hint_y=None, height=22))
        columns.add_widget(column)
    section.add_widget(columns)
    return section


def build_detail_content(deposit: Deposit, portfolio_total: float, on_back, on_edit, on_delete) -> ScrollView:
    metrics = calc.compute_metrics(deposit, portfolio_total)

    content = BoxLayout(orientation="vertical", size_hint_y=None, spacing=4)
    content.bind(minimum_height=content.setter("height"))
    content.add_widget(_build_header(on_back, on_edit, on_delete))
    content.add_widget(_build_hero(deposit, metrics))
    content.add_widget(_build_input_section(deposit, on_edit))
    content.add_widget(_build_computed_section(metrics))
    content.add_widget(_build_fire_section(metrics))

    scroll = ScrollView()
    scroll.add_widget(content)
    return scroll


class DepositDetailScreen(Screen):
    def update(self, deposit, portfolio_total, on_back, on_edit, on_delete):
        self.clear_widgets()
        self.add_widget(build_detail_content(deposit, portfolio_total, on_back, on_edit, on_delete))
```

- [ ] **Step 2: Manually verify the screen builds without error**

```bash
.venv/Scripts/python -c "
from datetime import date
from depositcalc.models import Deposit
from depositcalc.ui.deposit_detail_screen import DepositDetailScreen

deposit = Deposit(bank='Яндекс', date_from=date(2026,1,1), date_to=date(2026,1,31), amount=100000, rate=0.13, term_days=30, inflation=0.09, id=1)
screen = DepositDetailScreen(name='detail')
screen.update(deposit, portfolio_total=100000, on_back=lambda: None, on_edit=lambda: None, on_delete=lambda: None)
print(type(screen), len(screen.children))
"
```

Expected: prints the screen type and a nonzero child count, no traceback. This only checks the widget tree builds; visual details are only visible once `main.py` puts this screen in a real running window (Task 10).

- [ ] **Step 3: Commit**

```bash
git add src/depositcalc/ui/deposit_detail_screen.py
git commit -m "Add deposit detail screen with FIRE section"
```

---

### Task 10: App wiring

**Files:**
- Modify: `main.py` (replace the Task 1 placeholder `build()` body with real `ScreenManager`/storage wiring; keep the `sys.path` and font-registration lines at the top unchanged)

**Interfaces:**
- Consumes: `storage.*` (Task 4), `ui.portfolio_screen.PortfolioScreen` (Task 7), `ui.deposit_form_screen.DepositFormScreen` (Task 8), `ui.deposit_detail_screen.DepositDetailScreen` (Task 9).
- Produces: the runnable app (`DepositCalculatorApp`).

This task has no new pytest suite — it is the final integration point for a UI-only feature explicitly excluded from automated testing by spec §8.

- [ ] **Step 1: Replace the body of `main.py`**

Keep the existing `sys.path.insert(...)` and font-registration block at the top exactly as Task 1 left them. Replace everything from `from kivy.app import App` onward with:

```python
from kivy.app import App  # noqa: E402
from kivy.uix.screenmanager import ScreenManager, NoTransition  # noqa: E402

from depositcalc import storage  # noqa: E402
from depositcalc.ui.deposit_detail_screen import DepositDetailScreen  # noqa: E402
from depositcalc.ui.deposit_form_screen import DepositFormScreen  # noqa: E402
from depositcalc.ui.portfolio_screen import PortfolioScreen  # noqa: E402


class DepositCalculatorApp(App):
    def build(self):
        self.title = "Калькулятор вкладов"

        db_path = os.path.join(self.user_data_dir, "deposits.db")
        self.conn = storage.connect(db_path)

        self.portfolio_screen = PortfolioScreen(name="portfolio")
        self.detail_screen = DepositDetailScreen(name="detail")
        self.form_screen = DepositFormScreen(name="form")

        self.sm = ScreenManager(transition=NoTransition())
        self.sm.add_widget(self.portfolio_screen)
        self.sm.add_widget(self.detail_screen)
        self.sm.add_widget(self.form_screen)

        self.show_portfolio()
        return self.sm

    def show_portfolio(self):
        deposits = storage.get_all_deposits(self.conn)
        self.portfolio_screen.update(deposits, on_tap_deposit=self.show_detail, on_add=self.show_add_form)
        self.sm.current = "portfolio"

    def show_detail(self, deposit_id: int):
        deposit = storage.get_deposit(self.conn, deposit_id)
        total = sum(d.amount for d in storage.get_all_deposits(self.conn))
        self.detail_screen.update(
            deposit,
            portfolio_total=total,
            on_back=self.show_portfolio,
            on_edit=lambda: self.show_edit_form(deposit_id),
            on_delete=lambda: self._delete_and_return(deposit_id),
        )
        self.sm.current = "detail"

    def show_add_form(self):
        self.form_screen.show(on_save=self._save_new_deposit, on_cancel=self.show_portfolio)
        self.sm.current = "form"

    def show_edit_form(self, deposit_id: int):
        deposit = storage.get_deposit(self.conn, deposit_id)
        self.form_screen.show(
            on_save=self._save_edited_deposit,
            on_cancel=lambda: self.show_detail(deposit_id),
            deposit=deposit,
        )
        self.sm.current = "form"

    def _save_new_deposit(self, deposit):
        storage.add_deposit(self.conn, deposit)
        self.show_portfolio()

    def _save_edited_deposit(self, deposit):
        storage.update_deposit(self.conn, deposit)
        self.show_detail(deposit.id)

    def _delete_and_return(self, deposit_id):
        storage.delete_deposit(self.conn, deposit_id)
        self.show_portfolio()


if __name__ == "__main__":
    DepositCalculatorApp().run()
```

Kivy's `App.user_data_dir` creates the directory on first access, so no manual `os.makedirs` is needed.

- [ ] **Step 2: Run the full pytest suite one more time**

```bash
.venv/Scripts/pytest -v
```

Expected: every test from Tasks 2-5 still PASSes (`main.py` has no tests of its own, but this confirms the wiring didn't break an import elsewhere).

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "Wire storage and screens together into the running Kivy app"
```

---

## Follow-up (explicitly out of scope for this plan)

- Android packaging walkthrough (`buildozer -v android debug` run inside Google Colab, downloading the resulting APK, installing it on a device/emulator, and troubleshooting) — spec §9 defers this to a separate document written after this implementation and its tests are done, since the user runs the actual build herself.
- Bundling a Cyrillic-capable font inside the APK for the Android build (the `main.py` font-registration fallback added in Task 1/10 only covers the Windows desktop dev environment) — to be addressed in that same follow-up document.
