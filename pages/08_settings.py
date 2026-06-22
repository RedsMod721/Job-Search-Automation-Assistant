from __future__ import annotations

from app import render_settings
from src.ui.page_runner import run_page


def main() -> None:
    run_page("Settings", render_settings)


if __name__ == "__main__":
    main()
