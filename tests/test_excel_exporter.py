from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

import pandas as pd

from src.constants import PROJECT_ROOT
from src.excel_exporter import export_applications_to_excel


def test_export_applications_to_excel_uses_readable_columns() -> None:
    output_dir = PROJECT_ROOT / f"pytest-cache-files-excel-{uuid4().hex}"
    try:
        output_path = Path(
            export_applications_to_excel(
                [
                    {
                        "application_id": "app-1",
                        "company_name": "Acme AI",
                        "job_title": "AI Analyst",
                        "status": "To Apply",
                        "required_skills": ["Python", "SQL"],
                    }
                ],
                output_dir,
            )
        )

        assert output_path.exists()
        dataframe = pd.read_excel(output_path)
        assert "Company Name" in dataframe.columns
        assert dataframe.loc[0, "Company Name"] == "Acme AI"
        assert dataframe.loc[0, "Required Skills"] == "Python; SQL"
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
