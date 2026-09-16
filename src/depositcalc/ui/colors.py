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
