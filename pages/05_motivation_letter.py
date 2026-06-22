from __future__ import annotations

from app import render_motivation_letter
from src.ui.page_runner import run_page


def main() -> None:
    run_page("Motivation Letter", render_motivation_letter)


if __name__ == "__main__":
    main()
