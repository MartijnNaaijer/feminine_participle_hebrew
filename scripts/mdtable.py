"""Render a pandas DataFrame as a Markdown table (avoids the optional 'tabulate' dependency)."""
import pandas as pd


def to_md(df):
    df = df.copy()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [" / ".join(map(str, c)) for c in df.columns]
    idx = [" / ".join(map(str, i)) if isinstance(i, tuple) else str(i) for i in df.index]
    head = "| " + " | ".join([""] + [str(c) for c in df.columns]) + " |"
    sep = "|" + "---|" * (len(df.columns) + 1)
    rows = ["| " + " | ".join([i] + [str(v) for v in r]) + " |" for i, r in zip(idx, df.itertuples(index=False))]
    return "\n".join([head, sep] + rows)
