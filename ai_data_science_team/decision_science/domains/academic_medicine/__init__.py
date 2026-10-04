"""Academic medicine domain package."""

from .accreditation import AccreditationMetricSpec, AccreditationPack
from .admissions import AdmissionsPack, AdmissionsSchema
from .core import (
    AcademicMedicineDomainPack,
    AcademicMedicineMetricEngine,
    AcademicMedicineSchema,
    AcademicMedicineStudy,
    academic_medicine_metrics,
)
from .demo import demo_datasets, demo_metric_specs
from .executive import AcademicMedicineCQIEngine, CQIMetricSpec, DatasetRegistry, MetricResult, RegisteredDataset
from .gme import GMEPack, GMESchema
from .research import ResearchPack, ResearchSchema
from .ume import UMEPack, UMESchema
from .workforce import WorkforcePack, WorkforceSchema

__all__ = [
    "AccreditationMetricSpec",
    "AccreditationPack",
    "AcademicMedicineDomainPack",
    "AcademicMedicineMetricEngine",
    "AcademicMedicineSchema",
    "AcademicMedicineStudy",
    "AdmissionsPack",
    "AdmissionsSchema",
    "AcademicMedicineCQIEngine",
    "CQIMetricSpec",
    "DatasetRegistry",
    "MetricResult",
    "RegisteredDataset",
    "GMEPack",
    "GMESchema",
    "ResearchPack",
    "ResearchSchema",
    "UMEPack",
    "UMESchema",
    "WorkforcePack",
    "WorkforceSchema",
    "academic_medicine_metrics",
    "demo_datasets",
    "demo_metric_specs",
]
