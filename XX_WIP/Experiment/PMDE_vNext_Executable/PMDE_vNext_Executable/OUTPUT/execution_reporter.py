from datetime import datetime, UTC
import pandas as pd


class ExecutionReporter:

    def __init__(

        self,

        output_file,

        engine_name,

        version,

        run_mode,

        input_file
    ):

        self.output_file = output_file

        self.engine_name = engine_name

        self.version = version

        self.run_mode = run_mode

        self.input_file = input_file

        self.run_timestamp = (

            datetime.now(UTC)

            .strftime(
                "%Y%m%d_%H%M%S"
            )
        )

        self.rows = []

        self.success_count = 0

        self.failed_count = 0

        self.tactical_counts = {}

    #
    # RECORD SUCCESS
    #

    def record_success(

        self,
        row
    ):

        self.rows.append(row)

        self.success_count += 1

        tactical_state = (
            row["Final_State"]
        )

        self.tactical_counts[
            tactical_state
        ] = (

            self.tactical_counts.get(
                tactical_state,
                0
            ) + 1
        )

    #
    # RECORD FAILURE
    #

    def record_failure(

        self,
        symbol
    ):

        self.failed_count += 1

    #
    # FINALIZE REPORT
    #

    def finalize(

        self,
        total_symbols
    ):

        df_output = pd.DataFrame(
            self.rows
        )

        with open(

            self.output_file,

            "w",

            encoding="utf-8"

        ) as file:

            #
            # HEADER
            #

            file.write(
                f"ENGINE_NAME,"
                f"{self.engine_name}\n"
            )

            file.write(
                f"VERSION,"
                f"{self.version}\n"
            )

            file.write(
                f"RUN_TIMESTAMP,"
                f"{self.run_timestamp}\n"
            )

            file.write(
                f"INPUT_FILE,"
                f"{self.input_file}\n"
            )

            file.write("\n")

            #
            # EXECUTION SUMMARY
            #

            file.write(
                f"TOTAL_SYMBOLS,"
                f"{total_symbols}\n"
            )

            file.write(
                f"SUCCESS_COUNT,"
                f"{self.success_count}\n"
            )

            file.write(
                f"FAILED,"
                f"{self.failed_count}\n"
            )

            #
            # TACTICAL SUMMARY
            #

            for state, count in (

                self.tactical_counts
                .items()

            ):

                pct = round(

                    (
                        count /
                        max(
                            self.success_count,
                            1
                        )
                    ) * 100,

                    2
                )

                file.write(
                    f"{state},"
                    f"{count},"
                    f"{pct}%\n"
                )

            file.write(
                f"RUN_MODE,"
                f"{self.run_mode}\n"
            )

            file.write("\n")

        #
        # APPEND DATAFRAME
        #

        df_output.to_csv(

            self.output_file,

            mode="a",

            index=False
        )

        #
        # TERMINAL
        #

        print("")
        print("=" * 70)
        print(
            "PMDE EXECUTION COMPLETED"
        )
        print("=" * 70)

        print(
            f"TOTAL SYMBOLS : "
            f"{total_symbols}"
        )

        print(
            f"SUCCESS        : "
            f"{self.success_count}"
        )

        print(
            f"FAILED         : "
            f"{self.failed_count}"
        )

        print("")

        print(
            f"OUTPUT FILE:"
        )

        print(
            self.output_file
        )

        print("")
        print("=" * 70)