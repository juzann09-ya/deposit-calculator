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
from kivy.uix.widget import Widget

from depositcalc import calc
from depositcalc.models import Deposit
from depositcalc.ui.colors import bank_gradient
from depositcalc.ui.widgets import Badge, GradientCard, format_money, left_label


def _build_header(on_back, on_edit, on_delete) -> BoxLayout:
    row = BoxLayout(size_hint_y=None, height=48, padding=(8, 4))
    back_button = Button(
        text="← Назад", background_color=(0, 0, 0, 0), color=(0.2, 0.2, 0.2, 1),
        size_hint_x=None, width=95,
    )
    back_button.bind(on_release=lambda *_args: on_back())
    edit_button = Button(
        text="Изменить", background_color=(0, 0, 0, 0), color=(0.2, 0.2, 0.2, 1),
        size_hint_x=None, width=90,
    )
    edit_button.bind(on_release=lambda *_args: on_edit())
    delete_button = Button(
        text="Удалить", background_color=(0, 0, 0, 0), color=(0.8, 0.15, 0.15, 1),
        size_hint_x=None, width=90,
    )
    delete_button.bind(on_release=lambda *_args: on_delete())
    row.add_widget(back_button)
    row.add_widget(Widget(size_hint_x=1))
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
    badge_row.add_widget(Badge(f"Обещ.: +{format_money(metrics.promised_income)}"))
    badge_row.add_widget(Badge(f"Реальн.: +{format_money(metrics.real_income_total)}"))
    badge_row.add_widget(Label())  # spacer, keeps badges from stretching to full width
    hero.add_widget(badge_row)
    hero.add_widget(left_label(
        format_money(deposit.amount),
        bold=True, font_size=28, color=(0.05, 0.05, 0.05, 1), size_hint_y=None, height=40,
    ))
    return hero


class _FieldRow(ButtonBehavior, BoxLayout):
    """A tappable 'label ... value › row for the 'Вы вводите' section.

    Two left_label()s (one left-aligned, one right-aligned) rather than a
    single Button — Kivy Buttons have the same halign-needs-text_size
    limitation as Label, and cramming both pieces of text into one string
    can't align a label to the left and a value to the right independently.
    """


def _field_row(label: str, value: str, on_edit) -> _FieldRow:
    row = _FieldRow(size_hint_y=None, height=44, padding=(4, 0))
    row.add_widget(left_label(label, color=(0.15, 0.15, 0.15, 1)))
    row.add_widget(left_label(f"{value}  ›", halign="right", color=(0.15, 0.15, 0.15, 1)))
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
        "✎ Вы вводите", bold=True, color=(0.25, 0.45, 0.9, 1), size_hint_y=None, height=32,
    ))
    section.add_widget(_field_row("Банк", deposit.bank, on_edit))
    section.add_widget(_field_row("Дата открытия", deposit.date_from.isoformat(), on_edit))
    section.add_widget(_field_row("Дата закрытия", deposit.date_to.isoformat(), on_edit))
    section.add_widget(_field_row("Сумма", format_money(deposit.amount), on_edit))
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
        "🧮 Рассчитывается автоматически",
        bold=True, color=(0.55, 0.55, 0.55, 1), size_hint_y=None, height=32,
    ))
    section.add_widget(subheading("Номинальная доходность"))
    section.add_widget(_computed_row("Рост суммы", f"{metrics.nominal_growth:.4f}"))
    section.add_widget(_computed_row("Доходность", f"{metrics.nominal_yield:.2%}"))
    section.add_widget(subheading("Реальная доходность (с поправкой на инфляцию)"))
    section.add_widget(_computed_row("Рост инфляции за срок", f"{metrics.inflation_growth:.4f}"))
    section.add_widget(_computed_row("Инфляция за срок", f"{metrics.inflation_over_term:.2%}"))
    section.add_widget(_computed_row("Реальная доходность", f"{metrics.real_yield:.2%}"))
    section.add_widget(_computed_row("Реальный доход за срок", format_money(metrics.real_income_total)))
    section.add_widget(_computed_row(
        "Реальный доход в день", format_money(metrics.real_income_per_day, decimals=1)
    ))
    section.add_widget(subheading("Портфель"))
    section.add_widget(_computed_row("Доля в портфеле", f"{metrics.portfolio_share:.0%}"))
    section.add_widget(_computed_row("Дней до закрытия", str(metrics.days_to_close)))
    return section


def _build_fire_section(metrics: calc.DepositMetrics) -> BoxLayout:
    section = BoxLayout(orientation="vertical", size_hint_y=None, padding=(12, 8), spacing=4)
    section.bind(minimum_height=section.setter("height"))
    section.add_widget(left_label(
        "🔥 FIRE", bold=True, color=(0.55, 0.55, 0.55, 1), size_hint_y=None, height=32,
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
        column.add_widget(left_label(f"В год: {format_money(annual)}", size_hint_y=None, height=22))
        column.add_widget(left_label(f"В месяц: {format_money(monthly)}", size_hint_y=None, height=22))
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
