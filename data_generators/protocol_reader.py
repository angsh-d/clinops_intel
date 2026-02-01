"""Reads the 3 protocol USDM JSONs and returns a ProtocolContext dataclass."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from data_generators.config import PROTOCOL_DIR


@dataclass
class VisitDef:
    visit_id: str
    name: str
    visit_type: str
    timing_value: int | None
    timing_unit: str
    timing_relative_to: str
    window_early: int | None
    window_late: int | None
    recurrence_pattern: str | None = None
    recurrence_start_cycle: int | None = None
    recurrence_end_cycle: int | None = None


@dataclass
class ActivityDef:
    activity_id: str
    name: str
    category: str
    domain: str


@dataclass
class ScheduledInstance:
    instance_id: str
    visit_id: str
    activity_id: str
    activity_name: str
    is_required: bool


@dataclass
class CriterionDef:
    criterion_id: str
    type: str  # Inclusion / Exclusion
    original_text: str


@dataclass
class ArmDef:
    arm_id: str
    arm_name: str
    arm_type: str
    planned_subjects: int


@dataclass
class StratFactor:
    name: str
    levels: list[str]


@dataclass
class ProtocolContext:
    study_id: str = ""
    nct_number: str = ""
    official_title: str = ""
    phase: str = ""
    target_enrollment: int = 595
    planned_sites: int = 150
    countries: list[str] = field(default_factory=list)
    cycle_length_days: int = 21
    max_cycles: int = 6
    screening_window_days: int = 28
    visits: list[VisitDef] = field(default_factory=list)
    activities: list[ActivityDef] = field(default_factory=list)
    scheduled_instances: list[ScheduledInstance] = field(default_factory=list)
    inclusion_criteria: list[CriterionDef] = field(default_factory=list)
    exclusion_criteria: list[CriterionDef] = field(default_factory=list)
    arms: list[ArmDef] = field(default_factory=list)
    stratification_factors: list[StratFactor] = field(default_factory=list)


def _find_json(pattern: str) -> Path:
    matches = sorted(PROTOCOL_DIR.glob(pattern))
    if not matches:
        raise FileNotFoundError(f"No file matching {pattern} in {PROTOCOL_DIR}")
    return matches[0]


def _load(path: Path) -> dict:
    with open(path, "r") as f:
        return json.load(f)


def _parse_usdm(data: dict, ctx: ProtocolContext) -> None:
    study = data.get("study", {})
    ctx.study_id = study.get("id", "M14-359")
    ctx.official_title = study.get("officialTitle", "")
    ctx.nct_number = ""
    for sid in study.get("studyIdentifiers", []):
        if sid.get("scopeId") == "clinicaltrials.gov":
            ctx.nct_number = sid["id"]
            break
    phase_info = study.get("studyPhase", {})
    ctx.phase = phase_info.get("decode", "Phase 3")
    design = study.get("studyDesignInfo", {})
    ctx.target_enrollment = design.get("targetEnrollment", 595)
    ctx.planned_sites = design.get("plannedSites", 150)
    countries_raw = design.get("countries", {}).get("values", [])
    ctx.countries = countries_raw if countries_raw else [
        "USA", "Japan", "Australia", "New Zealand", "Canada",
        "United Kingdom", "Spain", "Germany", "Netherlands", "Denmark",
        "Finland", "Hungary", "Czechia", "Russia", "Turkey",
        "Argentina", "South Korea", "Taiwan", "Israel", "South Africa",
    ]
    milestones = study.get("studyMilestones", {})
    ctx.screening_window_days = milestones.get("estimatedDurations", {}).get("screeningPeriodDays", 28)
    # Arms
    for sd in study.get("studyDesigns", []):
        for arm in sd.get("studyArms", []):
            ctx.arms.append(ArmDef(
                arm_id=arm.get("id", ""),
                arm_name=arm.get("name", ""),
                arm_type=arm.get("type", {}).get("decode", "") if isinstance(arm.get("type"), dict) else str(arm.get("type", "")),
                planned_subjects=arm.get("plannedSubjects", 0),
            ))
        for sf in sd.get("studyStratificationFactors", []):
            levels = []
            for lv in sf.get("levels", []):
                levels.append(lv.get("value", lv.get("decode", str(lv))))
            ctx.stratification_factors.append(StratFactor(
                name=sf.get("name", sf.get("factorName", "")),
                levels=levels,
            ))


def _parse_soa(data: dict, ctx: ProtocolContext) -> None:
    for v in data.get("visits", []):
        timing = v.get("timing", {})
        window = v.get("window") or {}
        recurrence = v.get("recurrence") or {}
        ctx.visits.append(VisitDef(
            visit_id=v["id"],
            name=v.get("name", ""),
            visit_type=v.get("visitType", ""),
            timing_value=timing.get("value"),
            timing_unit=timing.get("unit", "days"),
            timing_relative_to=timing.get("relativeTo", ""),
            window_early=window.get("earlyBound"),
            window_late=window.get("lateBound"),
            recurrence_pattern=recurrence.get("pattern"),
            recurrence_start_cycle=recurrence.get("startCycle"),
            recurrence_end_cycle=recurrence.get("endCycle"),
        ))
    for a in data.get("activities", []):
        ctx.activities.append(ActivityDef(
            activity_id=a["id"],
            name=a.get("name", ""),
            category=a.get("category", ""),
            domain=a.get("domain", ""),
        ))
    for si in data.get("scheduledActivityInstances", []):
        ctx.scheduled_instances.append(ScheduledInstance(
            instance_id=si.get("id", ""),
            visit_id=si.get("encounterId", ""),
            activity_id=si.get("activityId", ""),
            activity_name=si.get("activityName", ""),
            is_required=si.get("isRequired", True),
        ))


def _parse_eligibility(data: dict, ctx: ProtocolContext) -> None:
    for c in data.get("criteria", []):
        cdef = CriterionDef(
            criterion_id=c["criterionId"],
            type=c.get("type", ""),
            original_text=c.get("originalText", ""),
        )
        if cdef.type == "Inclusion":
            ctx.inclusion_criteria.append(cdef)
        else:
            ctx.exclusion_criteria.append(cdef)


def load_protocol_context() -> ProtocolContext:
    ctx = ProtocolContext()
    usdm_path = _find_json("*_usdm_4.0_*.json")
    soa_path = _find_json("*_soa_usdm_draft_*.json")
    elig_path = _find_json("*_eligibility_criteria_*.json")
    _parse_usdm(_load(usdm_path), ctx)
    _parse_soa(_load(soa_path), ctx)
    _parse_eligibility(_load(elig_path), ctx)
    return ctx
