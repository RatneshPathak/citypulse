"""Date conversion for historical replay datasets."""

import pandas as pd


def shift_date_columns(frame: pd.DataFrame, columns: tuple[str, ...], delta: pd.Timedelta) -> None:
    for column in columns:
        if column in frame.columns:
            frame[column] = pd.to_datetime(frame[column], errors="raise") + delta
