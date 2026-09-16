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
        self._date_warning_acknowledged = False

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
        if date_to < date_from and not self._date_warning_acknowledged:
            self._date_warning_acknowledged = True
            self._message_label.text = (
                "Внимание: дата закрытия раньше даты открытия. "
                "Нажмите «Сохранить» ещё раз, чтобы продолжить."
            )
            return

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
