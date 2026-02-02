"""Generate enrollment tables: screening_log, randomization_log, enrollment_velocity."""

from datetime import date, timedelta

import numpy as np
from numpy.random import Generator
from sqlalchemy.orm import Session

from data_generators.anomaly_profiles import ANOMALY_PROFILES, REGIONAL_CLUSTER_SITES
from data_generators.config import SNAPSHOT_DATE, STUDY_START, STUDY_WEEKS
from data_generators.distributions import (
    SF_CODE_WEIGHTS, enrollment_s_curve, generate_narrative, seasonal_factor,
)
from data_generators.models import (
    EnrollmentVelocity, RandomizationLog, ScreeningLog, Site,
)
from data_generators.protocol_reader import ProtocolContext

# Per-site base monthly screening rates by experience level
_EXP_MONTHLY_RATE = {"High": 0.4, "Medium": 0.25, "Low": 0.15}

# Weeks to continue screening after enrollment cap is reached (pipeline wind-down)
_POST_CAP_WIND_DOWN_WEEKS = 8


def generate_enrollment(
    session: Session, ctx: ProtocolContext, rng: Generator
) -> dict[str, int]:
    """Generate screening_log, randomization_log, and enrollment_velocity.

    Strategy: Per-site Poisson arrivals scaled by the S-curve derivative to
    control the global enrollment pace. Screening continues for several weeks
    after the enrollment cap (595) is reached, simulating pipeline wind-down
    where sites complete in-progress screenings but no new randomizations occur.
    """
    sites: list[Site] = session.query(Site).all()
    target_total = ctx.target_enrollment  # 595

    screening_rows: list[dict] = []
    randomization_rows: list[dict] = []
    subject_counter = 0
    total_randomized = 0
    enrollment_close_week: int | None = None

    # Block randomization per site (blocks of 4: AABB permuted)
    site_arm_blocks: dict[str, list[str]] = {}

    # Track per-site randomization counts to cap at site target
    site_randomized: dict[str, int] = {s.site_id: 0 for s in sites}

    # Pre-compute weekly S-curve scale factor: fraction of peak rate
    weekly_deriv = []
    for w in range(STUDY_WEEKS + 1):
        c_now = enrollment_s_curve(w)
        c_prev = enrollment_s_curve(w - 1) if w > 0 else 0
        weekly_deriv.append(max(0, c_now - c_prev))
    peak_deriv = max(weekly_deriv) if weekly_deriv else 1
    weekly_scale = [d / peak_deriv for d in weekly_deriv]

    for week_num in range(STUDY_WEEKS + 1):
        week_start = STUDY_START + timedelta(weeks=week_num)
        if week_start > SNAPSHOT_DATE:
            break

        # Stop after wind-down period
        if enrollment_close_week is not None and week_num > enrollment_close_week + _POST_CAP_WIND_DOWN_WEEKS:
            break

        scale = weekly_scale[week_num] if week_num < len(weekly_scale) else 0.01
        # After enrollment closes, decay screening rate over wind-down weeks
        if enrollment_close_week is not None:
            weeks_since_close = week_num - enrollment_close_week
            scale *= max(0, 1.0 - weeks_since_close * 0.12)
            if scale <= 0:
                break

        if scale < 0.02:
            continue
        season = seasonal_factor(week_start)

        for site in sites:
            if site.activation_date > week_start:
                continue

            weeks_active = (week_start - site.activation_date).days / 7
            ramp = 0.5 if weeks_active < 6 else 1.0

            # Base weekly rate = monthly / 4.33
            base_weekly = _EXP_MONTHLY_RATE.get(site.experience_level, 1.0) / 4.33
            rate = base_weekly * scale * season * ramp

            # Anomaly overrides
            prof = ANOMALY_PROFILES.get(site.site_id)
            if prof:
                if prof.get("screening_rate_multiplier"):
                    # For competing-trial sites, only apply multiplier before competition starts
                    if prof.get("competing_trial_start_week") and week_num >= prof["competing_trial_start_week"]:
                        pass  # don't apply pre-competition boost after competition starts
                    # For monitoring-anxiety sites, only apply multiplier before frequency change
                    elif prof.get("monitoring_frequency_change_date") and week_start >= prof["monitoring_frequency_change_date"]:
                        pass  # don't apply pre-change boost after monitoring increase
                    else:
                        rate *= prof["screening_rate_multiplier"]
                if prof.get("competing_trial_start_week") and week_num >= prof["competing_trial_start_week"]:
                    rate *= (1.0 - prof["screening_drop_pct"])
                if prof.get("enrollment_drop_during_spike_pct") and prof.get("cra_transition_date"):
                    cra_date = prof["cra_transition_date"]
                    delay_wk = prof.get("enrollment_drop_delay_weeks", 3)
                    spike_start = cra_date + timedelta(weeks=delay_wk)
                    spike_end = spike_start + timedelta(weeks=prof.get("lag_spike_duration_weeks", 6))
                    if spike_start <= week_start <= spike_end:
                        rate *= (1.0 - prof["enrollment_drop_during_spike_pct"])
                # Monitoring anxiety: enrollment drops after monitoring frequency increase
                if prof.get("post_increase_enrollment_drop") and prof.get("monitoring_frequency_change_date"):
                    if week_start >= prof["monitoring_frequency_change_date"]:
                        rate *= (1.0 - prof["post_increase_enrollment_drop"])

            # Ensure anomaly and regional cluster sites have minimum meaningful enrollment
            # for pattern detection. Disable floor when anomaly profile intentionally
            # suppresses the rate (competing trial drop, CRA-transition enrollment drop)
            # so the decline is visible.
            is_anomaly = prof is not None
            is_regional = site.site_id in REGIONAL_CLUSTER_SITES
            apply_floor = True
            if prof and prof.get("competing_trial_start_week"):
                if week_num >= prof["competing_trial_start_week"]:
                    apply_floor = False
            if prof and prof.get("enrollment_drop_during_spike_pct") and prof.get("cra_transition_date"):
                cra_date = prof["cra_transition_date"]
                delay_wk = prof.get("enrollment_drop_delay_weeks", 3)
                drop_start = cra_date + timedelta(weeks=delay_wk)
                drop_end = drop_start + timedelta(weeks=prof.get("lag_spike_duration_weeks", 6))
                if drop_start <= week_start <= drop_end:
                    apply_floor = False
            if (is_anomaly or is_regional) and apply_floor:
                # Enrollment stall: reduced floor so stall is visible (30-50% enrollment)
                if prof and prof.get("anomaly_type") == "enrollment_stall":
                    floor = 0.15
                else:
                    floor = 0.40  # ~1 screening every 2-3 weeks minimum
                # Monitoring anxiety: reduce floor after frequency change (visible drop)
                if prof and prof.get("post_increase_enrollment_drop") and prof.get("monitoring_frequency_change_date"):
                    if week_start >= prof["monitoring_frequency_change_date"]:
                        floor *= (1.0 - prof["post_increase_enrollment_drop"])
                rate = max(rate, floor)

            # Chain 2: boost screening rate during stockout windows so consent
            # withdrawal pattern is clearly visible in the data
            if prof and prof.get("stockout_episodes"):
                for ep in prof["stockout_episodes"]:
                    ep_start = ep["start"]
                    ep_end = ep_start + timedelta(days=ep["duration_days"])
                    if ep_start - timedelta(days=7) <= week_start <= ep_end + timedelta(days=14):
                        rate = max(rate, 0.80)
                        break

            n_screen = int(rng.poisson(max(rate, 0.01)))
            if n_screen == 0:
                continue

            for _ in range(n_screen):
                subject_counter += 1
                subject_id = f"SUBJ-{subject_counter:05d}"
                screen_date = week_start + timedelta(days=int(rng.integers(0, 7)))
                if screen_date > SNAPSHOT_DATE:
                    continue

                # Screen failure rate
                if prof and prof.get("screen_failure_rate"):
                    sf_rate = prof["screen_failure_rate"]
                    if prof.get("post_competition_sf_rate") and prof.get("competing_trial_start_week"):
                        if week_num >= prof["competing_trial_start_week"]:
                            sf_rate = prof["post_competition_sf_rate"]
                else:
                    sf_rate = float(rng.beta(7, 20))
                # Monitoring anxiety: SF rate increases after monitoring frequency change
                if prof and prof.get("post_increase_sf_rate_bump") and prof.get("monitoring_frequency_change_date"):
                    if screen_date >= prof["monitoring_frequency_change_date"]:
                        sf_rate += prof["post_increase_sf_rate_bump"]

                passed = rng.random() > sf_rate
                failure_code = None
                failure_narrative = None
                outcome = "Passed"

                # Chain 2: PASSED subjects withdraw consent during stockout
                if passed and prof and prof.get("consent_withdrawals_during_stockout"):
                    for ep in prof.get("stockout_episodes", []):
                        ep_start = ep["start"]
                        ep_end = ep_start + timedelta(days=ep["duration_days"])
                        if ep_start <= screen_date <= ep_end + timedelta(days=14):
                            if rng.random() < 0.67:  # 2/3 subjects withdraw consent
                                passed = False
                                outcome = "Failed"
                                failure_code = "SF_CONSENT"
                                failure_narrative = generate_narrative(rng, "SF_CONSENT", "moderate")
                            break

                if not passed:
                    outcome = "Failed"
                    if failure_code is None:  # not already set by Chain 2
                        codes = list(SF_CODE_WEIGHTS.keys())
                        weights = list(SF_CODE_WEIGHTS.values())

                        if prof and prof.get("overrepresented_sf_codes"):
                            mult = prof.get("sf_code_multiplier", 3.0)
                            for oc in prof["overrepresented_sf_codes"]:
                                if oc in SF_CODE_WEIGHTS:
                                    idx_c = codes.index(oc)
                                    weights[idx_c] *= mult
                            total_w = sum(weights)
                            weights = [w / total_w for w in weights]

                        failure_code = str(rng.choice(codes, p=weights))

                        country = site.country
                        if country == "JPN":
                            tier = rng.choice(["detailed", "moderate", "terse"], p=[0.5, 0.35, 0.15])
                        elif country == "USA":
                            tier = rng.choice(["detailed", "moderate", "terse"], p=[0.3, 0.5, 0.2])
                        else:
                            tier = rng.choice(["detailed", "moderate", "terse"], p=[0.2, 0.4, 0.4])

                        failure_narrative = generate_narrative(rng, failure_code, tier)

                screening_rows.append({
                    "site_id": site.site_id,
                    "subject_id": subject_id,
                    "screening_date": screen_date,
                    "outcome": outcome,
                    "failure_reason_code": failure_code,
                    "failure_reason_narrative": failure_narrative,
                })

                if passed and total_randomized < target_total and site_randomized[site.site_id] < site.target_enrollment:
                    rand_date = screen_date + timedelta(days=int(rng.integers(1, 14)))
                    if rand_date > SNAPSHOT_DATE:
                        rand_date = SNAPSHOT_DATE

                    # Block randomization (blocks of 4 per site)
                    arm = _next_arm(rng, site.site_id, site_arm_blocks)

                    gender = rng.choice(["Male", "Female"], p=[0.6, 0.4])
                    ecog = rng.choice(["0", "1"], p=[0.45, 0.55])

                    randomization_rows.append({
                        "site_id": site.site_id,
                        "subject_id": subject_id,
                        "randomization_date": rand_date,
                        "arm_code": arm,
                        "stratum_gender": gender,
                        "stratum_ecog": ecog,
                    })
                    total_randomized += 1
                    site_randomized[site.site_id] += 1
                    if total_randomized >= target_total and enrollment_close_week is None:
                        enrollment_close_week = week_num

    session.bulk_insert_mappings(ScreeningLog, screening_rows)
    session.bulk_insert_mappings(RandomizationLog, randomization_rows)
    session.flush()

    velocity_rows = _compute_velocity(session, sites)
    session.bulk_insert_mappings(EnrollmentVelocity, velocity_rows)
    session.flush()

    return {
        "screening_log": len(screening_rows),
        "randomization_log": len(randomization_rows),
        "enrollment_velocity": len(velocity_rows),
    }


def _next_arm(rng: Generator, site_id: str, blocks: dict[str, list[str]]) -> str:
    """Return next arm from permuted block randomization (blocks of 4)."""
    if site_id not in blocks or not blocks[site_id]:
        blocks[site_id] = list(rng.permutation(["ARM_A", "ARM_A", "ARM_B", "ARM_B"]))
    return blocks[site_id].pop(0)


def _compute_velocity(session: Session, sites: list[Site]) -> list[dict]:
    """Compute weekly enrollment velocity from individual screening/randomization records."""
    rows: list[dict] = []
    all_screening = session.query(ScreeningLog).all()
    all_rand = session.query(RandomizationLog).all()

    screen_by_site_week: dict[str, dict[int, list]] = {}
    rand_by_site_week: dict[str, dict[int, list]] = {}

    for s in all_screening:
        wk = (s.screening_date - STUDY_START).days // 7
        screen_by_site_week.setdefault(s.site_id, {}).setdefault(wk, []).append(s)

    for r in all_rand:
        wk = (r.randomization_date - STUDY_START).days // 7
        rand_by_site_week.setdefault(r.site_id, {}).setdefault(wk, []).append(r)

    for site in sites:
        sid = site.site_id
        act_week = max(0, (site.activation_date - STUDY_START).days // 7)
        cum_screened = 0
        cum_randomized = 0

        for wk in range(act_week, STUDY_WEEKS + 1):
            week_start = STUDY_START + timedelta(weeks=wk)
            if week_start > SNAPSHOT_DATE:
                break

            s_list = screen_by_site_week.get(sid, {}).get(wk, [])
            r_list = rand_by_site_week.get(sid, {}).get(wk, [])

            screened = len(s_list)
            failed = sum(1 for s in s_list if s.outcome == "Failed")
            randomized = len(r_list)

            cum_screened += screened
            cum_randomized += randomized
            target_cum = int(round(site.target_enrollment * min(1.0, wk / max(1, STUDY_WEEKS))))

            rows.append({
                "site_id": sid,
                "week_start": week_start,
                "week_number": wk,
                "screened_count": screened,
                "screen_failed_count": failed,
                "randomized_count": randomized,
                "cumulative_screened": cum_screened,
                "cumulative_randomized": cum_randomized,
                "target_cumulative": target_cum,
            })

    return rows
