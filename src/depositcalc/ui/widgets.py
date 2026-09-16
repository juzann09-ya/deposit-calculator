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


def format_money(value: float, decimals: int = 0) -> str:
    """Format a ruble amount with space-separated thousands, e.g. '100 000 ₽'."""
    return f"{value:,.{decimals}f} ₽".replace(",", " ")


def left_label(text: str, **kwargs) -> Label:
    """A Label whose `halign`/`valign` actually take effect (Kivy ignores
    both unless `text_size` tracks the widget's own size)."""
    kwargs.setdefault("halign", "left")
    kwargs.setdefault("valign", "middle")
    label = Label(text=text, **kwargs)
    label.bind(size=lambda inst, size: setattr(inst, "text_size", size))
    return label
