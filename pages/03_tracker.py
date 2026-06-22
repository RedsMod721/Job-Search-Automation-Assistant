from __future__ import annotations

from app import render_tracker
from src.ui.page_runner import run_page


def main() -> None:
    run_page("Tracker", render_tracker)


if __name__ == "__main__":
    main()
