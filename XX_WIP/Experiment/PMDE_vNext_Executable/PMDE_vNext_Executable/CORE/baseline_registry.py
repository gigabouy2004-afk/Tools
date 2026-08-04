from pathlib import Path
import pandas as pd


BASELINE_PATH = Path(
    "STORAGE/ACTIVE_BASELINE.csv"
)


class BaselineRegistry:

    REQUIRED_COLUMNS = [
        "symbol",
        "timestamp",
        "l1_state",
        "tactical_state"
    ]

    @staticmethod
    def validate_output_location():

        #
        # STORAGE DIRECTORY
        #

        storage_dir = BASELINE_PATH.parent

        if not storage_dir.exists():

            storage_dir.mkdir(
                parents=True,
                exist_ok=True
            )

        #
        # FILE ACCESS TEST
        #

        try:

            with open(
                BASELINE_PATH,
                "a",
                encoding="utf-8"
            ):
                pass

        except Exception as error:

            raise PermissionError(

                f"Cannot access "
                f"baseline file: "
                f"{BASELINE_PATH} "
                f"=> {error}"
            )

    @staticmethod
    def load():

        BaselineRegistry.validate_output_location()

        #
        # FILE DOES NOT EXIST
        #

        if not BASELINE_PATH.exists():

            return pd.DataFrame()

        #
        # EMPTY FILE
        #

        if BASELINE_PATH.stat().st_size == 0:

            return pd.DataFrame()

        #
        # READ CSV
        #

        try:

            df = pd.read_csv(
                BASELINE_PATH
            )

        except Exception as error:

            raise RuntimeError(

                f"Failed to read "
                f"baseline file => "
                f"{error}"
            )

        #
        # VALIDATE MINIMUM SCHEMA
        #

        missing = [

            col

            for col in
            BaselineRegistry.REQUIRED_COLUMNS

            if col not in df.columns
        ]

        if missing:

            raise RuntimeError(

                f"Baseline file "
                f"schema invalid. "
                f"Missing columns: "
                f"{missing}"
            )

        return df

    @staticmethod
    def update(record: dict):

        BaselineRegistry.validate_output_location()

        #
        # LOAD EXISTING
        #

        df = BaselineRegistry.load()

        #
        # REMOVE OLD SYMBOL
        #

        if not df.empty:

            df = df[
                df["symbol"] != record["symbol"]
            ]

        #
        # APPEND NEW RECORD
        #

        updated = pd.concat(

            [
                df,
                pd.DataFrame([record])
            ],

            ignore_index=True
        )

        #
        # ATOMIC WRITE
        #

        temp_path = (
            BASELINE_PATH.with_suffix(
                ".tmp"
            )
        )

        try:

            updated.to_csv(
                temp_path,
                index=False
            )

            #
            # REPLACE ONLY
            # AFTER SUCCESSFUL WRITE
            #

            temp_path.replace(
                BASELINE_PATH
            )

        except Exception as error:

            raise RuntimeError(

                f"Failed to update "
                f"baseline registry => "
                f"{error}"
            )