from __future__ import annotations

from app import render_company_search
from src.ui.page_runner import run_page


def main() -> None:
    run_page("Company Search", render_company_search)


if __name__ == "__main__":
    main()
