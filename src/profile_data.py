import sys
import pandas as pd

def load(path):
    if path.lower().endswith((".xlsx", ".xls")):
        return pd.read_excel(path)
    return pd.read_csv(path, low_memory=False)

def main():
    if len(sys.argv) < 2:
        print("Usage: python src/profile_data.py data/raw/file.csv")
        return
    df = load(sys.argv[1])
    pd.set_option("display.width", 200, "display.max_columns", 50)
    print("SHAPE:", df.shape)
    print("\nCOLUMNS AND TYPES:\n", df.dtypes)
    print("\nFIRST 5 ROWS:\n", df.head())
    print("\nMISSING VALUES (%):\n", (df.isna().mean() * 100).round(1).sort_values(ascending=False))
    print("\nDUPLICATE ROWS:", int(df.duplicated().sum()))
    for col in df.columns:
        low = col.lower()
        if any(k in low for k in ("date", "time", "day")):
            parsed = pd.to_datetime(df[col], errors="coerce")
            if parsed.notna().any():
                print(f"\nDATE RANGE in '{col}': {parsed.min()} -> {parsed.max()}")
        if any(k in low for k in ("station", "site", "city", "location")):
            print(f"\nUNIQUE in '{col}': {df[col].nunique()}")
            print(df[col].value_counts().head(10))

if __name__ == "__main__":
    main()
