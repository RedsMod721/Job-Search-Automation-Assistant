from __future__ import annotations

from app import render_form_helper
from src.ui.page_runner import run_page


def main() -> None:
    run_page("Form Helper", render_form_helper)


if __name__ == "__main__":
    main()
