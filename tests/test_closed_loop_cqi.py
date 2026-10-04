from ai_data_science_team import (
    AcademicMedicineCQIEngine,
    AccreditationEvidencePackage,
    ActionStatus,
    DatasetRegistry,
    LeadershipActionRegistry,
    demo_datasets,
    demo_metric_specs,
)


def _engine_and_snapshot():
    registry = DatasetRegistry()
    for name, data in demo_datasets().items():
        registry.register(name, data, source=f"demo {name}", version="1")
    engine = AcademicMedicineCQIEngine(registry=registry)
    snapshot = engine.snapshot(demo_metric_specs())
    trends = engine.trends(demo_metric_specs())
    return engine, snapshot, trends


def test_exception_metrics_create_owned_actions_once():
    engine, snapshot, _ = _engine_and_snapshot()
    registry = LeadershipActionRegistry()
    exceptions = engine.exceptions(snapshot)

    created = registry.create_from_exceptions(exceptions)
    created_again = registry.create_from_exceptions(exceptions)

    assert len(created) == len(exceptions)
    assert created_again == []
    assert registry.summary()["TOTAL"] == len(exceptions)


def test_action_update_and_decision_log():
    engine, snapshot, _ = _engine_and_snapshot()
    registry = LeadershipActionRegistry()
    action = registry.create_from_exceptions(engine.exceptions(snapshot))[0]

    registry.update_action(
        action.action_id,
        status=ActionStatus.IN_PROGRESS,
        owner="CQI Lead",
        action="Implement corrective plan.",
        success_criterion="Return to target.",
    )
    decision = registry.record_decision(
        metric_id=action.metric_id,
        action_id=action.action_id,
        decision="Approve corrective plan",
        rationale="Metric breached threshold.",
        decision_maker="Dean",
        options_considered=["Do nothing", "Targeted intervention"],
        evidence_record_ids=action.evidence_record_ids,
    )

    assert registry.actions[0].status == ActionStatus.IN_PROGRESS
    assert decision.decision_maker == "Dean"
    assert registry.summary()["DECISIONS"] == 1


def test_outcome_review_verifies_success_and_reopens_failure():
    registry = LeadershipActionRegistry()
    action = registry.create_action(
        metric_id="m1",
        metric_name="Metric 1",
        domain="UME",
        trigger_status="CRITICAL",
        trigger_value=0.80,
        owner="UME",
        action="Correct performance gap.",
        rationale="Threshold breach.",
        success_criterion="Reach target.",
        target_value=0.95,
    )

    failed = registry.review_outcome(
        action_id=action.action_id,
        measured_value=0.90,
        metric_status="WARNING",
        reviewer="CQI",
    )
    assert failed.success_met is False
    assert registry.actions[0].status == ActionStatus.OPEN

    registry.update_action(action.action_id, status=ActionStatus.COMPLETE)
    success = registry.review_outcome(
        action_id=action.action_id,
        measured_value=0.96,
        metric_status="ON_TARGET",
        reviewer="CQI",
    )
    assert success.success_met is True
    assert registry.actions[0].status == ActionStatus.VERIFIED


def test_action_registry_round_trips_json():
    registry = LeadershipActionRegistry()
    action = registry.create_action(
        metric_id="m2",
        metric_name="Metric 2",
        domain="GME",
        trigger_status="WARNING",
        trigger_value=0.75,
        owner="GME",
        action="Run intervention.",
        rationale="Threshold warning.",
        success_criterion="Reach configured target.",
    )
    registry.record_decision(
        metric_id=action.metric_id,
        action_id=action.action_id,
        decision="Proceed",
        rationale="Evidence supports intervention.",
        decision_maker="Committee",
    )

    restored = LeadershipActionRegistry.from_json(registry.to_json())
    assert restored.actions[0].metric_id == "m2"
    assert restored.decisions[0].decision == "Proceed"


def test_accreditation_evidence_packet_links_metric_action_decision_and_review():
    engine, snapshot, trends = _engine_and_snapshot()
    exceptions = engine.exceptions(snapshot)
    assert not exceptions.empty

    registry = LeadershipActionRegistry()
    action = registry.create_from_exceptions(exceptions)[0]
    registry.record_decision(
        metric_id=action.metric_id,
        action_id=action.action_id,
        decision="Approve action",
        rationale="Threshold breach requires response.",
        decision_maker="Dean",
        evidence_record_ids=action.evidence_record_ids,
    )

    current = snapshot.loc[snapshot["metric_id"] == action.metric_id].iloc[-1]
    registry.review_outcome(
        action_id=action.action_id,
        measured_value=float(current["value"]),
        metric_status=str(current["status"]),
        reviewer="CQI Lead",
        evidence_record_ids=[str(current["evidence_record_id"])],
    )

    packet = AccreditationEvidencePackage.build(
        metric_id=action.metric_id,
        snapshot=snapshot,
        trends=trends,
        ledger=engine.ledger,
        actions=registry,
    )

    assert packet["metric"]["metric_id"] == action.metric_id
    assert packet["leadership_actions"]
    assert packet["decision_log"]
    assert packet["outcome_reviews"]
    markdown = AccreditationEvidencePackage.to_markdown(packet)
    assert "Leadership actions" in markdown
    assert "Decision log" in markdown
    assert "Outcome verification" in markdown
