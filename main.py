"""Kivy App entry point. Buildozer packages the repo with this file at the root.

Full screen/storage wiring lands in Task 10 of the implementation plan.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from kivy.core.text import LabelBase  # noqa: E402  (must run before any widget is built)

_WINDOWS_FONT_DIR = r"C:\Windows\Fonts"
_ARIAL_REGULAR = os.path.join(_WINDOWS_FONT_DIR, "arial.ttf")
_ARIAL_BOLD = os.path.join(_WINDOWS_FONT_DIR, "arialbd.ttf")
_ARIAL_ITALIC = os.path.join(_WINDOWS_FONT_DIR, "ariali.ttf")
_ARIAL_BOLD_ITALIC = os.path.join(_WINDOWS_FONT_DIR, "arialbi.ttf")
if os.path.exists(_ARIAL_REGULAR):
    # Overrides Kivy's default "Roboto" font family with one that reliably
    # renders Cyrillic on this desktop dev machine. See Global Constraints.
    # Registering all four style slots (falling back to the regular face
    # individually for any missing variant) keeps bold=True labels actually
    # bold instead of silently falling back to regular app-wide.
    LabelBase.register(
        name="Roboto",
        fn_regular=_ARIAL_REGULAR,
        fn_bold=_ARIAL_BOLD if os.path.exists(_ARIAL_BOLD) else _ARIAL_REGULAR,
        fn_italic=_ARIAL_ITALIC if os.path.exists(_ARIAL_ITALIC) else _ARIAL_REGULAR,
        fn_bolditalic=_ARIAL_BOLD_ITALIC if os.path.exists(_ARIAL_BOLD_ITALIC) else _ARIAL_REGULAR,
    )

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
        if deposit is None:
            self.show_portfolio()
            return
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

    def on_stop(self):
        self.conn.close()


if __name__ == "__main__":
    DepositCalculatorApp().run()
