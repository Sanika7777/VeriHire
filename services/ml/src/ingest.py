"""Load, validate and split the EMSCAD dataset. Split happens here, before
any fitting, to avoid leakage (DATA.md §5)."""

import hashlib
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

RAW_PATH = Path(__file__).parent.parent / "data" / "raw" / "fake_job_postings.csv"
PROCESSED_DIR = Path(__file__).parent.parent / "data" / "processed"
SEED = 42

REQUIRED_COLUMNS = [
    "job_id",
    "title",
    "location",
    "department",
    "salary_range",
    "company_profile",
    "description",
    "requirements",
    "benefits",
    "telecommuting",
    "has_company_logo",
    "has_questions",
    "employment_type",
    "required_experience",
    "required_education",
    "industry",
    "function",
    "fraudulent",
]


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_raw() -> pd.DataFrame:
    if not RAW_PATH.exists():
        raise FileNotFoundError(
            f"{RAW_PATH} not found. See DATA.md for download instructions."
        )
    df = pd.read_csv(RAW_PATH)
    missing = set(REQUIRED_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"Dataset is missing expected columns: {missing}")
    return df


def split_and_save() -> dict[str, int]:
    df = load_raw()

    train_df, temp_df = train_test_split(
        df, test_size=0.30, stratify=df["fraudulent"], random_state=SEED
    )
    val_df, test_df = train_test_split(
        temp_df, test_size=0.50, stratify=temp_df["fraudulent"], random_state=SEED
    )

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    train_df.to_parquet(PROCESSED_DIR / "train.parquet", index=False)
    val_df.to_parquet(PROCESSED_DIR / "val.parquet", index=False)
    test_df.to_parquet(PROCESSED_DIR / "test.parquet", index=False)

    counts = {"train": len(train_df), "val": len(val_df), "test": len(test_df)}

    datacard = PROCESSED_DIR / "datacard.md"
    datacard.write_text(
        "# Datacard — EMSCAD fake job postings\n\n"
        f"- Source file: `{RAW_PATH.name}`\n"
        f"- SHA-256: `{_file_hash(RAW_PATH)}`\n"
        f"- Total rows: {len(df)}\n"
        f"- Fraudulent rows: {int(df['fraudulent'].sum())} "
        f"({df['fraudulent'].mean() * 100:.2f}%)\n"
        f"- Split (stratified, seed={SEED}): train={counts['train']}, "
        f"val={counts['val']}, test={counts['test']}\n"
        "- Split performed before any feature fitting (no leakage).\n"
    )

    return counts


if __name__ == "__main__":
    result = split_and_save()
    print(f"Split complete: {result}")
