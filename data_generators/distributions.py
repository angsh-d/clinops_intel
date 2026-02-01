"""Reusable statistical distributions and helper functions."""

from datetime import date, timedelta

import numpy as np
from numpy.random import Generator


def enrollment_s_curve(t: float, K: int = 595, r: float = 0.055, t_mid: float = 65.0) -> float:
    """Logistic S-curve: cumulative enrollment at week t."""
    return K / (1.0 + np.exp(-r * (t - t_mid)))


def seasonal_factor(d: date) -> float:
    """Enrollment rate multiplier for seasonal dips."""
    md = (d.month, d.day)
    if (12, 15) <= md or md <= (1, 15):
        return 0.60  # -40% holiday
    if d.month == 8:
        return 0.75  # -25% summer
    return 1.0


ENTRY_LAG_PARAMS: dict[str, tuple[float, float]] = {
    # North America
    "USA": (1.0, 0.7),
    "CAN": (1.1, 0.7),
    # Western Europe
    "GBR": (1.1, 0.7),
    "DEU": (1.1, 0.7),
    "NLD": (1.1, 0.7),
    "ESP": (1.1, 0.7),
    "DNK": (1.1, 0.7),
    "FIN": (1.1, 0.7),
    # Eastern Europe
    "HUN": (1.3, 0.8),
    "CZE": (1.3, 0.8),
    "RUS": (1.3, 0.8),
    "TUR": (1.3, 0.8),
    # East Asia
    "JPN": (0.5, 0.5),
    "KOR": (0.5, 0.5),
    "TWN": (0.5, 0.5),
    # Oceania
    "AUS": (1.3, 0.8),
    "NZL": (1.2, 0.8),
    # South America
    "ARG": (1.4, 0.9),
    # Middle East
    "ISR": (1.0, 0.7),
    # Africa
    "ZAF": (1.5, 0.9),
}


def entry_lag_sample(rng: Generator, region: str, n: int = 1) -> np.ndarray:
    """Sample entry lag in days from LogNormal per region."""
    mu, sigma = ENTRY_LAG_PARAMS.get(region, (1.0, 0.7))
    return np.maximum(1, np.round(rng.lognormal(mu, sigma, n))).astype(int)


def is_holiday_window(d: date) -> bool:
    """Dec 15 – Jan 5 holiday window for entry lag adjustments."""
    md = (d.month, d.day)
    return (12, 15) <= md or md <= (1, 5)


# ── Screen failure narrative templates ────────────────────────────────────────

_NARRATIVES: dict[str, dict[str, list[str]]] = {
    "SF_ECOG": {
        "detailed": [
            "Patient presented with ECOG PS of 2, assessed during screening visit. Functional status declined since referral due to disease progression.",
            "ECOG performance status evaluated at 2 by investigator. Patient reports fatigue limiting daily activities consistent with PS 2.",
            "Screening assessment revealed ECOG PS 2. Patient ambulatory but unable to carry out work activities, consistent with borderline eligibility.",
        ],
        "moderate": [
            "ECOG PS 2, does not meet inclusion criterion for PS 0-1.",
            "Patient ECOG score of 2, excluded per protocol.",
            "ECOG performance status 2, not eligible.",
        ],
        "terse": [
            "ECOG 2",
            "PS 2 - screen fail",
            "ECOG ineligible",
        ],
    },
    "SF_HISTO": {
        "detailed": [
            "Histological review confirmed squamous cell carcinoma, not non-squamous NSCLC as required by protocol.",
            "Pathology report reviewed at screening: squamous histology confirmed on biopsy specimen. Does not meet inclusion criterion 3.",
        ],
        "moderate": [
            "Squamous histology confirmed, non-squamous required.",
            "Histology exclusion - squamous NSCLC.",
        ],
        "terse": [
            "Squamous histology",
            "Wrong histology",
        ],
    },
    "SF_ORGAN": {
        "detailed": [
            "Screening labs showed creatinine clearance of 42 mL/min (required ≥60 mL/min). Hepatic function also borderline with AST 2.8x ULN.",
            "Inadequate organ function: ANC 1.2 x10^9/L (req ≥1.5), platelets 85 x10^9/L (req ≥100). Patient referred back to treating physician.",
        ],
        "moderate": [
            "Organ function criteria not met: renal insufficiency.",
            "Lab values out of range - inadequate hepatic function.",
        ],
        "terse": [
            "Organ function fail",
            "Labs OOR",
        ],
    },
    "SF_PRIOR_CHEMO": {
        "detailed": [
            "Patient received prior carboplatin/pemetrexed for metastatic disease 8 months ago. Protocol requires no prior systemic chemotherapy for advanced/metastatic disease.",
            "Medical history review revealed prior docetaxel treatment for metastatic NSCLC, excluding patient per inclusion criterion 12.",
        ],
        "moderate": [
            "Prior systemic chemotherapy for metastatic disease.",
            "Previous chemo for advanced NSCLC, not eligible.",
        ],
        "terse": [
            "Prior chemo",
            "Prior systemic tx",
        ],
    },
    "SF_SMOKING": {
        "detailed": [
            "Patient is a never-smoker with no documented smoking history. Protocol requires current or former smoker status with at least 20 pack-years.",
            "Smoking history review: patient reports 8 pack-years, below the 20 pack-year minimum required by inclusion criterion 5.",
        ],
        "moderate": [
            "Insufficient smoking history (<20 pack-years).",
            "Never-smoker, does not meet smoking criterion.",
        ],
        "terse": [
            "Never smoker",
            "Smoking hx insufficient",
        ],
    },
    "SF_BRAIN_METS": {
        "detailed": [
            "MRI of the brain at screening revealed 2 untreated brain metastases (8mm and 12mm). Patient excluded per exclusion criterion 5.",
        ],
        "moderate": [
            "Untreated brain metastases on screening MRI.",
            "Brain mets present, excluded.",
        ],
        "terse": [
            "Brain mets",
            "CNS disease",
        ],
    },
    "SF_CONSENT": {
        "detailed": [
            "Patient withdrew consent during screening period citing personal reasons. No further details documented.",
            "Subject decided not to proceed with study participation after initial screening assessments were completed.",
        ],
        "moderate": [
            "Consent withdrawn during screening.",
            "Patient declined participation.",
        ],
        "terse": [
            "Consent withdrawn",
            "Patient declined",
        ],
    },
    "SF_NEUROPATHY": {
        "detailed": [
            "Patient presents with grade 2 peripheral neuropathy in lower extremities, likely related to prior taxane exposure.",
        ],
        "moderate": [
            "Grade 2 peripheral neuropathy, excluded.",
        ],
        "terse": [
            "Neuropathy G2",
        ],
    },
    "SF_CARDIAC": {
        "detailed": [
            "ECG screening revealed QTc prolongation (490ms) and patient reports NYHA Class II heart failure symptoms.",
        ],
        "moderate": [
            "Cardiac risk factors present, excluded per protocol.",
        ],
        "terse": [
            "Cardiac exclusion",
        ],
    },
    "SF_EGFR_ALK": {
        "detailed": [
            "Molecular testing positive for EGFR exon 19 deletion. Patient has not received prior targeted therapy. Must receive TKI first per protocol.",
        ],
        "moderate": [
            "EGFR mutation positive, no prior targeted therapy.",
        ],
        "terse": [
            "EGFR+ untreated",
        ],
    },
    "SF_MEASURABLE": {
        "detailed": [
            "CT scan review shows no measurable lesions per RECIST 1.1 criteria. All lesions are below 10mm in longest diameter.",
        ],
        "moderate": [
            "No measurable disease per RECIST 1.1.",
        ],
        "terse": [
            "No measurable disease",
        ],
    },
    "SF_AGE": {
        "moderate": [
            "Patient age below 18 years.",
        ],
        "terse": [
            "Age < 18",
        ],
    },
    "SF_OTHER": {
        "detailed": [
            "Patient excluded due to active secondary malignancy (Stage II breast cancer diagnosed 6 months ago, currently on treatment).",
            "Patient has uncontrolled diabetes with HbA1c of 10.2%. Does not meet study entry requirements.",
        ],
        "moderate": [
            "Active secondary malignancy.",
            "Prohibited concomitant medication.",
            "Uncontrolled comorbidity.",
        ],
        "terse": [
            "Other exclusion",
            "Comorbidity",
        ],
    },
}

# Failure reason distribution weights (baseline)
SF_CODE_WEIGHTS: dict[str, float] = {
    "SF_ECOG": 0.18,
    "SF_HISTO": 0.15,
    "SF_ORGAN": 0.20,
    "SF_PRIOR_CHEMO": 0.12,
    "SF_SMOKING": 0.08,
    "SF_BRAIN_METS": 0.05,
    "SF_CONSENT": 0.05,
    "SF_NEUROPATHY": 0.04,
    "SF_CARDIAC": 0.03,
    "SF_EGFR_ALK": 0.03,
    "SF_MEASURABLE": 0.03,
    "SF_AGE": 0.01,
    "SF_OTHER": 0.03,
}


def generate_narrative(rng: Generator, reason_code: str, quality_tier: str) -> str:
    """Generate a free-text screen failure narrative."""
    templates = _NARRATIVES.get(reason_code, _NARRATIVES["SF_OTHER"])
    tier_templates = templates.get(quality_tier)
    if not tier_templates:
        # fall through tiers
        for t in ["moderate", "terse", "detailed"]:
            if t in templates:
                tier_templates = templates[t]
                break
    if not tier_templates:
        return f"Screen failure: {reason_code}"
    return str(rng.choice(tier_templates))


# ── CRF page types mapped from SOA activities ────────────────────────────────
CRF_PAGES = [
    "Lab Results",
    "Tumor Assessment",
    "Adverse Events",
    "Drug Accountability",
    "Vital Signs",
    "Physical Exam",
    "Concomitant Medications",
]

CRF_PAGE_WEIGHTS = [0.30, 0.20, 0.15, 0.15, 0.08, 0.07, 0.05]

# Query type distribution
QUERY_TYPE_WEIGHTS = {
    "Missing Data": 0.35,
    "Discrepancy": 0.25,
    "Out of Range": 0.20,
    "Protocol Deviation": 0.10,
    "Logical Inconsistency": 0.10,
}

# Field names by CRF page for data corrections
CRF_FIELD_NAMES: dict[str, list[str]] = {
    "Lab Results": ["hemoglobin", "wbc_count", "platelet_count", "creatinine", "alt", "ast", "anc", "bilirubin"],
    "Tumor Assessment": ["target_lesion_1", "target_lesion_2", "non_target_status", "overall_response", "assessment_date"],
    "Adverse Events": ["ae_term", "ae_start_date", "ae_severity", "ae_relationship", "ae_outcome", "ae_action_taken"],
    "Drug Accountability": ["dose_administered", "dose_date", "dose_modification", "pills_dispensed", "pills_returned"],
    "Vital Signs": ["systolic_bp", "diastolic_bp", "heart_rate", "temperature", "weight", "height"],
    "Physical Exam": ["general_appearance", "respiratory", "cardiovascular", "neurological", "musculoskeletal"],
    "Concomitant Medications": ["medication_name", "indication", "start_date", "end_date", "dose", "route"],
}
