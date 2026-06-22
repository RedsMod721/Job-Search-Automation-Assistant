from __future__ import annotations

from collections.abc import Callable
from typing import Any

import streamlit as st


def run_page(page_title: str, renderer: Callable[[dict[str, dict[str, Any]]], None]) -> None:
    from app import bootstrap

    st.set_page_config(page_title=f"{page_title} - Job Search Automation Assistant", layout="wide")
    configs = bootstrap()
    st.title(page_title)
    renderer(configs)
