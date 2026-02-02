"""14 anomaly site profiles with override parameters for generators."""

from datetime import date

# Each profile is keyed by site_id and contains overrides that generators check.
ANOMALY_PROFILES: dict[str, dict] = {
    # ── High query burden ─────────────────────────────────────────────────
    "SITE-012": {
        "country": "USA",
        "anomaly_type": "high_query_burden",
        "query_rate_multiplier": 2.5,
        "correction_rate": 0.12,
        "completeness_offset": -15,  # pct points lower
        "experience_level": "High",  # ensure enough enrollment volume
        "description": "2.5x query rate, 12% correction rate, low completeness",
    },
    "SITE-045": {
        "country": "USA",
        "anomaly_type": "high_query_burden",
        "query_rate_multiplier": 2.0,
        "concentrated_pages": ["Lab Results", "Drug Accountability"],
        "experience_level": "High",
        "description": "2x rate concentrated on Lab Results + Drug Accountability CRFs",
    },
    "SITE-078": {
        "country": "CAN",
        "anomaly_type": "high_query_burden",
        "query_rate_multiplier": 2.2,
        "staff_turnover": True,
        "experience_level": "High",
        "description": "2.2x rate, staff turnover",
    },
    # ── Enrollment stall ──────────────────────────────────────────────────
    "SITE-031": {
        "country": "JPN",
        "anomaly_type": "enrollment_stall",
        "screen_failure_rate": 0.48,
        "overrepresented_sf_codes": ["SF_ECOG", "SF_SMOKING"],
        "sf_code_multiplier": 3.0,
        "experience_level": "High",  # needs high screening volume for SF pattern
        "description": "48% screen failure, strict PI interpretation (Chain 4: excess kit inventory)",
        # Chain 4: low enrollment → kits expire
        "kit_expiry_count": 4,
    },
    "SITE-055": {
        "country": "USA",
        "anomaly_type": "enrollment_stall",
        "screen_failure_rate": 0.42,
        "competing_trial_start_week": 35,
        "screening_drop_pct": 0.60,
        "post_competition_sf_rate": 0.15,
        "screening_rate_multiplier": 2.5,  # strong referral pipeline pre-competition
        "experience_level": "High",  # needs volume before competition starts
        "description": "42% failure, volume drops week 35 (competing trial ~Nov 2024) (Chain 6)",
    },
    "SITE-089": {
        "country": "AUS",
        "anomaly_type": "enrollment_stall",
        "screen_failure_rate": 0.45,
        "screening_rate_multiplier": 0.50,
        "experience_level": "Medium",  # ensure some enrollment despite rate reduction
        "description": "45% failure, 50% screening rate",
    },
    # ── Entry lag spike ───────────────────────────────────────────────────
    "SITE-022": {
        "country": "USA",
        "anomaly_type": "entry_lag_spike",
        "lag_spike_start": date(2024, 9, 15),
        "lag_spike_duration_weeks": 6,
        "lag_spike_days": 7,
        "cra_transition_date": date(2024, 9, 15),
        "experience_level": "High",
        "description": "CRA transition Sep 2024, +7 days for 6 weeks (Chain 1: query spike → enrollment decel)",
        # Chain 1 effects
        "query_rate_multiplier_during_spike": 2.0,
        "enrollment_drop_during_spike_pct": 0.40,
        "enrollment_drop_delay_weeks": 3,  # enrollment drops 3 weeks after CRA transition
        "monitoring_delay_weeks": 3,
    },
    "SITE-067": {
        "country": "CAN",
        "anomaly_type": "entry_lag_spike",
        "lag_spike_start": date(2024, 11, 1),
        "lag_spike_duration_weeks": 4,
        "lag_spike_days": 5,
        "experience_level": "Medium",
        "description": "Coordinator leave Nov 2024, +5 days for 4 weeks",
    },
    "SITE-103": {
        "country": "JPN",
        "anomaly_type": "entry_lag_spike",
        "lag_spike_start": date(2025, 1, 1),
        "lag_spike_duration_weeks": 5,
        "lag_spike_days": 6,
        "description": "IT migration Jan 2025, +6 days for 5 weeks (Chain 5: regional cluster)",
        # Chain 5: neighboring sites also affected
        "regional_cluster_sites": ["SITE-108", "SITE-112", "SITE-119"],
        "regional_cluster_lag_extra_days": 2.5,  # avg for neighbors
    },
    # ── Supply constraint ─────────────────────────────────────────────────
    "SITE-041": {
        "country": "NZL",
        "anomaly_type": "supply_constraint",
        "experience_level": "High",
        "screening_rate_multiplier": 2.0,  # strong referral pipeline
        "stockout_episodes": [
            {
                "start": date(2025, 3, 1),  # peak activity period for NZL site
                "duration_days": 20,
                "reason": "Customs hold at Auckland depot",
            },
            {
                "start": date(2025, 6, 10),
                "duration_days": 14,
                "reason": "Depot shipping delay",
            },
        ],
        "description": "2 stockout episodes (Chain 2: stockout → randomization pause → consent withdrawals)",
        # Chain 2 effects
        "consent_withdrawals_during_stockout": True,
    },
    "SITE-115": {
        "country": "AUS",
        "anomaly_type": "supply_constraint",
        "stockout_episodes": [
            {
                "start": date(2025, 3, 10),
                "duration_days": 8,
                "reason": "Weather delay at Melbourne depot",
            },
        ],
        "description": "1 stockout episode (weather)",
    },
    # ── Suspicious perfection ───────────────────────────────────────────
    "SITE-074": {
        "country": "HUN",
        "anomaly_type": "suspicious_perfection",
        "entry_lag_forced_range": (1, 2),
        "query_rate_multiplier": 0.05,
        "completeness_forced": 99.5,
        "correction_rate": 0.005,
        "variance_suppression": True,
        "experience_level": "Medium",
        "description": "Suspiciously perfect metrics — near-zero variance across all KRIs (Chain 7)",
    },
    # ── Monitoring anxiety ──────────────────────────────────────────────
    "SITE-017": {
        "country": "GBR",
        "anomaly_type": "monitoring_anxiety",
        "monitoring_frequency_change_date": date(2025, 2, 1),
        "monitoring_interval_after_weeks": 3,
        "post_increase_sf_rate_bump": 0.15,
        "post_increase_enrollment_drop": 0.30,
        "post_increase_lag_extra_days": 3,
        "screening_rate_multiplier": 2.0,  # strong pipeline for visible before/after contrast
        "experience_level": "High",
        "description": "Doubled monitoring frequency → enrollment drops, SF rate increases (Chain 8: audit anxiety)",
    },
    # ── Monitoring gap ────────────────────────────────────────────────────
    "SITE-033": {
        "country": "USA",
        "anomaly_type": "monitoring_gap",
        "missed_visits": 3,
        "gap_start": date(2024, 10, 15),  # widened: Oct 15 → Mar 15 = 5 months
        "gap_end": date(2025, 3, 15),     # captures 3+ visits at 6-8 week intervals
        "cra_reassignment_date": date(2024, 10, 15),
        "experience_level": "Medium",
        "description": "3+ missed visits Oct-Mar, CRA reassignment (Chain 3: query age drift, hidden data quality debt)",
    },
    "SITE-098": {
        "country": "JPN",
        "anomaly_type": "monitoring_gap",
        "missed_visits": 2,
        "gap_start": date(2024, 12, 1),  # widened to ensure 2+ visits fall in window
        "gap_end": date(2025, 4, 15),
        "description": "2 missed visits, travel restrictions",
    },
}

# Sites affected by regional cluster (Chain 5)
# experience_level ensures these sites have enough subjects for detectable lag patterns
REGIONAL_CLUSTER_SITES = {
    "SITE-108": {"country": "JPN", "lag_extra_days": 3, "lag_start": date(2025, 1, 5), "lag_weeks": 4, "experience_level": "High"},
    "SITE-112": {"country": "JPN", "lag_extra_days": 2, "lag_start": date(2025, 1, 3), "lag_weeks": 4, "experience_level": "High"},
    "SITE-119": {"country": "JPN", "lag_extra_days": 2, "lag_start": date(2025, 1, 7), "lag_weeks": 3, "experience_level": "Medium"},
}
