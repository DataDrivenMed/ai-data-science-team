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
    "GMEPack",
    "GMESchema",
    "ResearchPack",
    "ResearchSchema",
    "UMEPack",
    "UMESchema",
    "WorkforcePack",
    "WorkforceSchema",
    "academic_medicine_metrics",
]
