from __future__ import annotations

from app import render_dashboard
from src.ui.page_runner import run_page


def main() -> None:
    run_page("Dashboard", render_dashboard)


if __name__ == "__main__":
    main()
