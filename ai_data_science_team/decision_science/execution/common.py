from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np
import pandas as pd


@dataclass(slots=True)
class ExecutionResult:
    method: str
    n: int
    estimates: dict[str, Any] = field(default_factory=dict)
    diagnostics: dict[str, Any] = field(default_factory=dict)
    assumptions_checked: dict[str, bool | None] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def require_columns(data: pd.DataFrame, columns: list[str]) -> None:
    missing = [column for column in columns if column not in data.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def complete_cases(data: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    require_columns(data, columns)
    return data.loc[:, columns].dropna().copy()


def design_matrix(
    data: pd.DataFrame,
    predictors: list[str],
    *,
    add_intercept: bool = True,
) -> pd.DataFrame:
    require_columns(data, predictors)
    frame = pd.get_dummies(
        data[predictors],
        drop_first=True,
        dtype=float,
    ).astype(float)
    if add_intercept:
        frame.insert(0, "const", 1.0)
    return frame


def coefficient_table(result: Any) -> dict[str, dict[str, float]]:
    names = list(result.model.exog_names)
    params = np.asarray(result.params)
    bse = np.asarray(result.bse)
    pvalues = np.asarray(result.pvalues)
    conf = np.asarray(result.conf_int())
    output: dict[str, dict[str, float]] = {}
    for index, name in enumerate(names):
        output[str(name)] = {
            "estimate": float(params[index]),
            "standard_error": float(bse[index]),
            "p_value": float(pvalues[index]),
            "ci_low": float(conf[index, 0]),
            "ci_high": float(conf[index, 1]),
        }
    return output
