"""Feature engineering for the content-risk fraud model.

Text (TF-IDF word + char n-grams) is fit on train only; everything else here
is a pure function of a single row so it never leaks across the split.
"""

import re

import numpy as np
import pandas as pd
import scipy.sparse as sp
from sklearn.feature_extraction.text import TfidfVectorizer

TEXT_COLUMNS = ["title", "company_profile", "description", "requirements"]

_PERSONAL_EMAIL_RE = re.compile(
    r"\b[a-zA-Z0-9._%+-]+@(gmail|yahoo|hotmail|outlook|rediffmail)\.com\b", re.IGNORECASE
)
_MESSAGING_HANDLE_RE = re.compile(r"\b(whatsapp|telegram|wa\.me|t\.me)\b", re.IGNORECASE)
_ADVANCE_FEE_RE = re.compile(
    r"\b(registration fee|processing fee|security deposit|pay(?:ment)? to (?:secure|confirm)|"
    r"refundable deposit|advance payment)\b",
    re.IGNORECASE,
)
_URGENCY_RE = re.compile(
    r"\b(urgent(?:ly)?|immediate(?:ly)? (?:hiring|joining)|apply now|limited (?:seats|time)|"
    r"act now|hurry)\b",
    re.IGNORECASE,
)
_EMOJI_RE = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF]"
)


def _combined_text(df: pd.DataFrame) -> pd.Series:
    return (
        df[TEXT_COLUMNS]
        .fillna("")
        .agg(" ".join, axis=1)
        .str.strip()
    )


def _caps_ratio(text: str) -> float:
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    return sum(1 for c in letters if c.isupper()) / len(letters)


def engineered_features(df: pd.DataFrame) -> pd.DataFrame:
    """Hand-crafted risk features + metadata, one row per posting."""
    text = _combined_text(df)

    out = pd.DataFrame(index=df.index)
    out["has_company_logo"] = df["has_company_logo"].fillna(0).astype(int)
    out["has_questions"] = df["has_questions"].fillna(0).astype(int)
    out["telecommuting"] = df["telecommuting"].fillna(0).astype(int)
    out["missing_company_profile"] = df["company_profile"].isna().astype(int)
    out["missing_salary_range"] = df["salary_range"].isna().astype(int)
    out["description_length"] = df["description"].fillna("").str.len()
    out["title_length"] = df["title"].fillna("").str.len()

    out["has_personal_email"] = text.str.contains(_PERSONAL_EMAIL_RE).astype(int)
    out["has_messaging_handle"] = text.str.contains(_MESSAGING_HANDLE_RE).astype(int)
    out["has_advance_fee_phrase"] = text.str.contains(_ADVANCE_FEE_RE).astype(int)
    out["has_urgency_marker"] = text.str.contains(_URGENCY_RE).astype(int)
    out["all_caps_ratio"] = text.apply(_caps_ratio)
    out["emoji_count"] = text.apply(lambda t: len(_EMOJI_RE.findall(t)))

    for col in ("employment_type", "required_experience", "required_education"):
        dummies = pd.get_dummies(df[col].fillna("unknown"), prefix=col)
        out = pd.concat([out, dummies], axis=1)

    return out


class FeatureBuilder:
    """Fits TF-IDF vectorizers on train text; reuses them for val/test/serving."""

    def __init__(self) -> None:
        self.word_vectorizer = TfidfVectorizer(
            ngram_range=(1, 2), max_features=4_000, min_df=3, sublinear_tf=True
        )
        self.char_vectorizer = TfidfVectorizer(
            ngram_range=(3, 5), analyzer="char_wb", max_features=4_000, min_df=3
        )
        self._engineered_columns: list[str] | None = None

    def fit_transform(self, df: pd.DataFrame) -> sp.csr_matrix:
        text = _combined_text(df)
        word_matrix = self.word_vectorizer.fit_transform(text)
        char_matrix = self.char_vectorizer.fit_transform(text)

        engineered = engineered_features(df)
        self._engineered_columns = list(engineered.columns)

        return sp.hstack(
            [word_matrix, char_matrix, sp.csr_matrix(engineered.to_numpy(dtype=np.float64))]
        ).tocsr()

    def transform(self, df: pd.DataFrame) -> sp.csr_matrix:
        if self._engineered_columns is None:
            raise RuntimeError("FeatureBuilder must be fit before transform.")

        text = _combined_text(df)
        word_matrix = self.word_vectorizer.transform(text)
        char_matrix = self.char_vectorizer.transform(text)

        engineered = engineered_features(df)
        engineered = engineered.reindex(columns=self._engineered_columns, fill_value=0)

        return sp.hstack(
            [word_matrix, char_matrix, sp.csr_matrix(engineered.to_numpy(dtype=np.float64))]
        ).tocsr()

    def feature_names(self) -> list[str]:
        assert self._engineered_columns is not None
        return [
            *self.word_vectorizer.get_feature_names_out().tolist(),
            *self.char_vectorizer.get_feature_names_out().tolist(),
            *self._engineered_columns,
        ]
