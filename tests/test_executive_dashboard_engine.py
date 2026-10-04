import pandas as pd

from ai_data_science_team import (
    AcademicMedicineCQIEngine,
    CQIMetricSpec,
    DatasetRegistry,
    demo_datasets,
    demo_metric_specs,
)


def test_dataset_registry_tracks_fingerprint_and_inventory():
    registry = DatasetRegistry()
    data = pd.DataFrame({"x": [1, 2, 3]})
    registered = registry.register(
        "sample",
        data,
        source="unit test",
        version="v1",
    )
    assert registered.fingerprint
    inventory = registry.inventory()
    assert inventory.iloc[0]["rows"] == 3
    assert inventory.iloc[0]["columns"] == 1


def test_cqi_engine_computes_snapshot_and_evidence():
    registry = DatasetRegistry()
    for name, data in demo_datasets().items():
        registry.register(name, data, source=f"demo {name}", version="1")
    engine = AcademicMedicineCQIEngine(registry=registry)
    specs = demo_metric_specs()
    snapshot = engine.snapshot(specs)
    assert len(snapshot) == len(specs)
    assert set(snapshot["status"]).issubset(
        {"ON_TARGET", "MONITOR", "WARNING", "CRITICAL", "NO_DATA"}
    )
    assert len(engine.ledger.records) == len(specs)
    assert snapshot["dataset_fingerprint"].notna().all()


def test_cqi_engine_generates_longitudinal_trends():
    registry = DatasetRegistry()
    for name, data in demo_datasets().items():
        registry.register(name, data, source=f"demo {name}", version="1")
    engine = AcademicMedicineCQIEngine(registry=registry)
    trends = engine.trends(demo_metric_specs())
    assert not trends.empty
    assert {"2023", "2024", "2025", "2026"}.issubset(set(trends["period"]))
    assert trends.groupby("metric_id").size().min() >= 4


def test_cqi_engine_flags_warning_and_critical_thresholds():
    registry = DatasetRegistry()
    data = pd.DataFrame(
        {
            "applicant_id": [1, 2, 3, 4],
            "applied": [1, 1, 1, 1],
            "interviewed": [1, 1, 1, 1],
            "admitted": [1, 1, 1, 1],
            "matriculated": [1, 0, 0, 0],
        }
    )
    registry.register("admissions", data, source="test")
    engine = AcademicMedicineCQIEngine(registry=registry)
    spec = CQIMetricSpec(
        metric_id="yield",
        name="Yield",
        domain="Admissions",
        dataset="admissions",
        calculator="admissions.yield",
        owner="Admissions",
        source="test",
        target=0.60,
        warning_threshold=0.50,
        critical_threshold=0.35,
    )
    result = engine.compute(spec)
    assert result.value == 0.25
    assert result.status == "CRITICAL"
    exceptions = engine.exceptions(pd.DataFrame([result.to_dict()]))
    assert len(exceptions) == 1


def test_executive_brief_uses_same_metric_results():
    registry = DatasetRegistry()
    for name, data in demo_datasets().items():
        registry.register(name, data, source=f"demo {name}", version="1")
    engine = AcademicMedicineCQIEngine(registry=registry)
    snapshot = engine.snapshot(demo_metric_specs())
    trends = engine.trends(demo_metric_specs())
    brief = engine.executive_brief(
        snapshot,
        trends,
        institution_name="Test School of Medicine",
        as_of="2026-10-04",
    )
    assert "Test School of Medicine" in brief
    assert "Executive signal" in brief
    assert "Evidence note" in brief
    assert "2026-10-04" in brief
