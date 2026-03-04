"""
data_loader.py
--------------
Responsible for loading financial transaction data from CSV files.
Performs initial schema validation and returns a raw DataFrame.
"""

import os
import pandas as pd


# Only date + amount are truly required; all others will be synthesised if absent
REQUIRED_COLUMNS = {"date", "amount"}
OPTIONAL_COLUMNS = {"description", "transaction_type", "category"}
ALL_EXPECTED_COLUMNS = REQUIRED_COLUMNS | OPTIONAL_COLUMNS

# Common alternative column-name mappings (bank exports use many names)
_COL_ALIASES: dict[str, list[str]] = {
    "date":             ["transaction date", "txn date", "value date", "trans date", "posting date"],
    "amount":           ["transaction amount", "txn amount", "net amount", "debit/credit amount"],
    "description":      ["transaction description", "narration", "particulars", "remarks", "details", "memo",
                         "transaction details", "beneficiary", "payee", "transaction details"],
    "transaction_type": ["type", "txn type", "dr/cr", "debit/credit", "cr/dr"],
    "category":         ["expense category", "spending category"],
}

# Pairs of (debit-column-alias, credit-column-alias) recognised for
# bank exports that have separate withdrawal / deposit columns
_SPLIT_AMOUNT_PAIRS: list[tuple[str, str]] = [
    ("debit",                  "credit"),
    ("withdrawal amt(inr)",    "deposit amt(inr)"),
    ("withdrawal amount",      "deposit amount"),
    ("withdrawal",             "deposit"),
    ("debit amount",           "credit amount"),
    ("dr amount",              "cr amount"),
    ("dr",                     "cr"),
]


def load_transactions(filepath: str) -> pd.DataFrame:
    """
    Load transaction data from a CSV file.

    Parameters
    ----------
    filepath : str
        Absolute or relative path to the CSV file.

    Returns
    -------
    pd.DataFrame
        Raw DataFrame containing all transaction rows.

    Raises
    ------
    FileNotFoundError
        If the specified file path does not exist.
    ValueError
        If required columns are missing from the CSV.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Transaction file not found: {filepath}")

    df = pd.read_csv(filepath)

    # Normalise column names: lowercase and strip whitespace
    df.columns = [col.strip().lower() for col in df.columns]

    # Apply alias substitutions before validation
    _apply_aliases(df)

    # Merge split debit/credit columns before schema validation
    _merge_split_amount_columns(df)

    _validate_schema(df, filepath)

    # Inject default values for optional columns that are still absent
    df = _fill_missing_optional(df)

    print(f"[DataLoader] Loaded {len(df)} transactions from '{filepath}'")
    return df


def _merge_split_amount_columns(df: pd.DataFrame) -> None:
    """
    In-place: if the CSV has separate debit and credit columns but no 'amount',
    merge them into a single 'amount' column and derive 'transaction_type'.

    Handles HDFC (Debit/Credit), SBI (Withdrawal Amt/Deposit Amt), etc.
    """
    if "amount" in df.columns:
        return  # already present, nothing to do

    cols = set(df.columns)
    for debit_col, credit_col in _SPLIT_AMOUNT_PAIRS:
        if debit_col in cols and credit_col in cols:
            import numpy as np

            def _to_num(series: pd.Series) -> pd.Series:
                """Coerce a column to numeric, treating blanks/NaN as 0."""
                return (
                    pd.to_numeric(
                        series.astype(str)
                              .str.replace(r"[^\d.\-]", "", regex=True)
                              .replace("", "0"),
                        errors="coerce",
                    ).fillna(0)
                )

            deb = _to_num(df[debit_col])
            cre = _to_num(df[credit_col])

            # Amount is whichever side is non-zero; prefer credit if both
            df["amount"] = np.where(cre > 0, cre, deb)
            df["transaction_type"] = np.where(cre > 0, "credit", "debit")

            # Drop the originals so they don't confuse downstream steps
            df.drop(columns=[debit_col, credit_col], inplace=True)
            print(f"[DataLoader] Merged split columns ('{debit_col}'/'{credit_col}') → 'amount' + 'transaction_type'.")
            return


def _apply_aliases(df: pd.DataFrame) -> None:
    """
    In-place: rename aliased column names to canonical names.
    E.g. 'narration' -> 'description', 'dr/cr' -> 'transaction_type'.
    """
    rename_map: dict[str, str] = {}
    for canonical, aliases in _COL_ALIASES.items():
        if canonical not in df.columns:
            for alias in aliases:
                if alias in df.columns:
                    rename_map[alias] = canonical
                    break
    if rename_map:
        df.rename(columns=rename_map, inplace=True)
        print(f"[DataLoader] Column aliases applied: {rename_map}")


def _fill_missing_optional(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add columns that are absent with safe default values so the rest
    of the pipeline never needs to guard against missing columns.

    * description      -> 'Unknown'
    * transaction_type -> inferred from amount sign where possible, else 'debit'
    * category         -> '' (categorization.py will fill this)
    """
    if "description" not in df.columns:
        df["description"] = "Unknown"
        print("[DataLoader] 'description' column missing — defaulting to 'Unknown'.")

    if "transaction_type" not in df.columns:
        # Try to infer from sign: positive amounts treated as credit, negative as debit
        if pd.api.types.is_numeric_dtype(df["amount"]):
            df["transaction_type"] = df["amount"].apply(
                lambda v: "credit" if v > 0 else "debit"
            )
            print("[DataLoader] 'transaction_type' inferred from amount sign.")
        else:
            df["transaction_type"] = "debit"
            print("[DataLoader] 'transaction_type' missing — defaulting to 'debit'.")

    if "category" not in df.columns:
        df["category"] = ""

    return df


def _validate_schema(df: pd.DataFrame, filepath: str) -> None:
    """
    Validate that the DataFrame contains all required columns.

    Parameters
    ----------
    df : pd.DataFrame
        The loaded DataFrame to validate.
    filepath : str
        Source file path (used in error messages).

    Raises
    ------
    ValueError
        If one or more required columns are absent.
    """
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(
            f"Missing columns: {', '.join(sorted(missing))}. "
            f"Your CSV must have at least: date, amount."
        )

    extra = set(df.columns) - ALL_EXPECTED_COLUMNS
    if extra:
        print(f"[DataLoader] Note: Extra columns detected (will be ignored): {extra}")


def get_data_summary(df: pd.DataFrame) -> dict:
    """
    Return a high-level summary of the raw loaded dataset.

    Parameters
    ----------
    df : pd.DataFrame
        Raw transaction DataFrame.

    Returns
    -------
    dict
        Dictionary with keys: total_rows, columns, date_range, has_category.
    """
    summary = {
        "total_rows": len(df),
        "columns": list(df.columns),
        "has_category": "category" in df.columns,
        "raw_sample": df.head(3).to_dict(orient="records"),
    }
    return summary
