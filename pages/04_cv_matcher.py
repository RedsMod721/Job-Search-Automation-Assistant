from __future__ import annotations

from app import render_cv_matcher
from src.ui.page_runner import run_page


def main() -> None:
    run_page("CV Matcher", render_cv_matcher)


if __name__ == "__main__":
    main()
