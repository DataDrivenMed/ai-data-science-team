from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Callable


@dataclass(frozen=True, slots=True)
class BenchmarkCase:
    name: str
    payload: Any
    expected: Any
    criterion: Callable[[Any, Any], bool] | None = None


@dataclass(slots=True)
class BenchmarkResult:
    name: str
    passed: bool
    actual: Any
    expected: Any
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class BenchmarkSuite:
    def __init__(self, cases: list[BenchmarkCase]):
        self.cases = cases

    def run(self, function: Callable[[Any], Any]) -> list[BenchmarkResult]:
        results: list[BenchmarkResult] = []
        for case in self.cases:
            try:
                actual = function(case.payload)
                criterion = case.criterion or (lambda a, e: a == e)
                passed = bool(criterion(actual, case.expected))
                results.append(BenchmarkResult(case.name, passed, actual, case.expected))
            except Exception as exc:
                results.append(
                    BenchmarkResult(
                        case.name,
                        False,
                        None,
                        case.expected,
                        error=f"{type(exc).__name__}: {exc}",
                    )
                )
        return results

    @staticmethod
    def pass_rate(results: list[BenchmarkResult]) -> float:
        if not results:
            return 0.0
        return sum(result.passed for result in results) / len(results)
