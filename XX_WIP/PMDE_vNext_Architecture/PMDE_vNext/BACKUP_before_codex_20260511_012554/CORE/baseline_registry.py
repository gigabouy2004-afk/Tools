
"""CSV baseline registry management."""

import pandas as pd
from pathlib import Path


BASELINE_FILE = Path("STORAGE/ACTIVE_BASELINE.csv")


class BaselineRegistry:

    @staticmethod
    def load_baseline() -> pd.DataFrame:

        if not BASELINE_FILE.exists():
            return pd.DataFrame()

        return pd.read_csv(BASELINE_FILE)


    @staticmethod
    def update_baseline(record: dict):

        existing = BaselineRegistry.load_baseline()

        updated = pd.concat([
            existing,
            pd.DataFrame([record])
        ], ignore_index=True)

        updated.to_csv(BASELINE_FILE, index=False)
