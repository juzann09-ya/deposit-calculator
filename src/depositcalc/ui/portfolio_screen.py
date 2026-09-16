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
from depositcalc.ui.widgets import Badge, DashedPlaceholderCard, GradientCard, format_money, left_label


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
    badge_row.add_widget(Badge(f"+{format_money(metrics.promised_income)}"))
    badge_row.add_widget(Label())  # spacer so the badge doesn't stretch to full width
    card.add_widget(badge_row)
    card.add_widget(left_label(
        format_money(deposit.amount),
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
        format_money(total_amount), bold=True, font_size=22, color=(0.05, 0.05, 0.05, 1),
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
