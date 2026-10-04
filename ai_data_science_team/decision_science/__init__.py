"""Decision-grade controls for the AI Data Science Team."""

from .approvals import ApprovalGate, ApprovalRegistry, ApprovalStatus
from .benchmarking import BenchmarkCase, BenchmarkResult, BenchmarkSuite
from .contracts import (
    AnalysisContract,
    AnalysisType,
    DataQualityReport,
    DecisionOption,
    DecisionRecommendation,
    EvidenceStrength,
    MethodRecommendation,
    QualityIssue,
    ReviewFinding,
    ReviewReport,
    ReviewStatus,
)
from .data_quality import assess_data_quality
from .decision_intelligence import Scenario, rank_scenarios
from .domain_packs import ACADEMIC_MEDICINE, CLINICAL_RESEARCH, DomainPack
from .governance import GovernanceReport, check_governance
from .memory import InstitutionalKnowledgeStore, MetricDefinition
from .methods import recommend_methods
from .model_routing import ModelCapability, ModelRouter, TaskProfile
from .observability import ExecutionEvent, TraceRecorder
from .orchestrator import DecisionScienceOrchestrator, DecisionScienceRun
from .provenance import (
    EvidenceLedger,
    EvidenceRecord,
    fingerprint_dataframe,
    fingerprint_file,
)
from .red_team import RedTeamReport, red_team_analysis
from .reproducibility import ReproducibilityPackage
from .review import review_analysis

__all__ = [
    "ACADEMIC_MEDICINE",
    "CLINICAL_RESEARCH",
    "AnalysisContract",
    "AnalysisType",
    "ApprovalGate",
    "ApprovalRegistry",
    "ApprovalStatus",
    "BenchmarkCase",
    "BenchmarkResult",
    "BenchmarkSuite",
    "DataQualityReport",
    "DecisionOption",
    "DecisionRecommendation",
    "DecisionScienceOrchestrator",
    "DecisionScienceRun",
    "DomainPack",
    "EvidenceLedger",
    "EvidenceRecord",
    "EvidenceStrength",
    "ExecutionEvent",
    "GovernanceReport",
    "InstitutionalKnowledgeStore",
    "MethodRecommendation",
    "MetricDefinition",
    "ModelCapability",
    "ModelRouter",
    "QualityIssue",
    "RedTeamReport",
    "ReproducibilityPackage",
    "ReviewFinding",
    "ReviewReport",
    "ReviewStatus",
    "Scenario",
    "TaskProfile",
    "TraceRecorder",
    "assess_data_quality",
    "check_governance",
    "fingerprint_dataframe",
    "fingerprint_file",
    "rank_scenarios",
    "recommend_methods",
    "red_team_analysis",
    "review_analysis",
]
