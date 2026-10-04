from ai_data_science_team.decision_science import (
    ApprovalRegistry,
    BenchmarkCase,
    BenchmarkSuite,
    InstitutionalKnowledgeStore,
    MetricDefinition,
    ModelCapability,
    ModelRouter,
    Scenario,
    TaskProfile,
    TraceRecorder,
    rank_scenarios,
)


def test_approval_gate_blocks_until_approved():
    registry = ApprovalRegistry()
    gate = registry.require(
        "deploy",
        "deploy predictive model",
        "consequential production action",
    )
    assert gate.can_execute is False
    gate.approve("reviewer")
    assert gate.can_execute is True


def test_model_router_prefers_capability_without_overspending():
    router = ModelRouter(
        [
            ModelCapability(
                name="cheap",
                reasoning=3,
                coding=2,
                context=2,
                relative_cost=1,
            ),
            ModelCapability(
                name="strong",
                reasoning=5,
                coding=5,
                context=5,
                relative_cost=5,
            ),
        ]
    )
    chosen = router.choose(
        TaskProfile(
            task_type="classification",
            reasoning_required=3,
            coding_required=1,
            context_required=1,
            cost_sensitivity=4,
        )
    )
    assert chosen.name == "cheap"


def test_benchmark_suite_reports_pass_rate():
    suite = BenchmarkSuite(
        [
            BenchmarkCase("one", 2, 4),
            BenchmarkCase("two", 3, 6),
        ]
    )
    results = suite.run(lambda value: value * 2)
    assert BenchmarkSuite.pass_rate(results) == 1.0


def test_institutional_memory_serializes_metric_definition():
    store = InstitutionalKnowledgeStore()
    store.add_metric(
        MetricDefinition(
            name="retention",
            definition="Share retained",
            numerator="retained",
            denominator="eligible",
        )
    )
    payload = store.to_dict()
    assert payload["metrics"]["retention"]["numerator"] == "retained"


def test_scenarios_rank_by_explicit_utility():
    ranked = rank_scenarios(
        [
            Scenario("A", expected_value=100, implementation_cost=20),
            Scenario("B", expected_value=95, implementation_cost=5),
        ]
    )
    assert ranked[0].name == "B"


def test_trace_recorder_summarizes_execution():
    recorder = TraceRecorder()
    event = recorder.start("reviewer", "check results")
    event.tool_calls = 2
    recorder.finish(event, validation_status="pass")
    summary = recorder.summary()
    assert summary["events"] == 1
    assert summary["tool_calls"] == 2
    assert summary["failures"] == 0
