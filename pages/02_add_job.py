from __future__ import annotations

from app import render_add_job
from src.ui.page_runner import run_page


def main() -> None:
    run_page("Add Job", render_add_job)


if __name__ == "__main__":
    main()
