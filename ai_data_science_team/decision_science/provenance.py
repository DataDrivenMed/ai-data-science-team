from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class EvidenceRecord:
    record_id: str
    kind: str
    claim: str
    source: str
    transformation: str | None = None
    code_reference: str | None = None
    dataset_fingerprint: str | None = None
    validation_status: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def fingerprint_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def fingerprint_file(path: str | Path) -> str:
    with open(path, "rb") as f:
        return fingerprint_bytes(f.read())


def fingerprint_dataframe(data: Any) -> str:
    try:
        payload = data.to_csv(index=False).encode("utf-8")
    except AttributeError as exc:
        raise TypeError("data must support to_csv(index=False)") from exc
    return fingerprint_bytes(payload)


class EvidenceLedger:
    def __init__(self) -> None:
        self._records: list[EvidenceRecord] = []

    @property
    def records(self) -> tuple[EvidenceRecord, ...]:
        return tuple(self._records)

    def add(
        self,
        *,
        kind: str,
        claim: str,
        source: str,
        transformation: str | None = None,
        code_reference: str | None = None,
        dataset_fingerprint: str | None = None,
        validation_status: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> EvidenceRecord:
        raw = f"{kind}|{claim}|{source}|{len(self._records)}".encode("utf-8")
        record = EvidenceRecord(
            record_id=hashlib.sha256(raw).hexdigest()[:16],
            kind=kind,
            claim=claim,
            source=source,
            transformation=transformation,
            code_reference=code_reference,
            dataset_fingerprint=dataset_fingerprint,
            validation_status=validation_status,
            metadata=metadata or {},
        )
        self._records.append(record)
        return record

    def to_dict(self) -> dict[str, Any]:
        return {"records": [asdict(record) for record in self._records]}

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(
            self.to_dict(),
            indent=indent,
            sort_keys=True,
            default=str,
        )
