"""Generate IRT/Supply tables: kit_inventory, randomization_events, depot_shipments."""

from datetime import date, timedelta

import numpy as np
from numpy.random import Generator
from sqlalchemy.orm import Session

from data_generators.anomaly_profiles import ANOMALY_PROFILES
from data_generators.config import SNAPSHOT_DATE, STUDY_START
from data_generators.models import (
    DepotShipment, DrugKitType, KitInventory, RandomizationEvent,
    RandomizationLog, Site,
)
from data_generators.protocol_reader import ProtocolContext

_COUNTRY_DEPOT = {
    "USA": "DEPOT_US",
    "ARG": "DEPOT_AM",
    "CAN": "DEPOT_AM",
    "GBR": "DEPOT_EU_W",
    "ESP": "DEPOT_EU_W",
    "DEU": "DEPOT_EU_W",
    "NLD": "DEPOT_EU_W",
    "DNK": "DEPOT_EU_W",
    "FIN": "DEPOT_EU_W",
    "HUN": "DEPOT_EU_E",
    "CZE": "DEPOT_EU_E",
    "RUS": "DEPOT_EU_E",
    "TUR": "DEPOT_EU_E",
    "JPN": "DEPOT_JP",
    "KOR": "DEPOT_AP",
    "TWN": "DEPOT_AP",
    "AUS": "DEPOT_AP",
    "NZL": "DEPOT_AP",
    "ISR": "DEPOT_IL",
    "ZAF": "DEPOT_ZA",
}

_DEPOT_SHIPPING_DAYS = {
    "DEPOT_US": 3,
    "DEPOT_AM": 4,
    "DEPOT_EU_W": 3,
    "DEPOT_EU_E": 4,
    "DEPOT_JP": 2,
    "DEPOT_AP": 4,
    "DEPOT_IL": 3,
    "DEPOT_ZA": 5,
}

_DELAY_REASONS = {
    "Kit Stockout": 0.40,
    "System Issue": 0.30,
    "Stratification Error": 0.20,
    "Kit Labeling Error": 0.10,
}


def generate_irt_supply(
    session: Session, ctx: ProtocolContext, rng: Generator
) -> dict[str, int]:
    """Generate kit_inventory, randomization_events, depot_shipments."""
    sites = session.query(Site).all()
    site_map = {s.site_id: s for s in sites}
    subjects = session.query(RandomizationLog).order_by(RandomizationLog.randomization_date).all()
    kit_types = session.query(DrugKitType).all()
    kit_type_ids = [k.kit_type_id for k in kit_types]

    inv_rows: list[dict] = []
    event_rows: list[dict] = []
    shipment_rows: list[dict] = []

    # Track inventory per site per kit type
    inventory: dict[str, dict[str, int]] = {}
    for site in sites:
        inventory[site.site_id] = {}
        for kt in kit_type_ids:
            inventory[site.site_id][kt] = int(rng.integers(6, 11))  # initial 6-10

    # Build stockout windows for anomaly sites
    stockout_windows: dict[str, list[tuple[date, date]]] = {}
    for sid, prof in ANOMALY_PROFILES.items():
        if prof.get("stockout_episodes"):
            windows = []
            for ep in prof["stockout_episodes"]:
                windows.append((ep["start"], ep["start"] + timedelta(days=ep["duration_days"])))
            stockout_windows[sid] = windows

    # Generate randomization events for each subject
    for subj in subjects:
        site = site_map.get(subj.site_id)
        if not site:
            continue

        prof = ANOMALY_PROFILES.get(subj.site_id)
        rand_date = subj.randomization_date

        # Check if site is in stockout
        in_stockout = False
        stockout_reason = None
        if subj.site_id in stockout_windows:
            for ws, we in stockout_windows[subj.site_id]:
                if ws <= rand_date <= we:
                    in_stockout = True
                    # Find the reason
                    for ep in prof.get("stockout_episodes", []):
                        if ep["start"] == ws:
                            stockout_reason = ep["reason"]
                            break
                    break

        if in_stockout:
            event_type = "Delay"
            delay_reason = "Kit Stockout"
            delay_hours = int(rng.integers(48, 192))  # 2-8 days
            # Consume from inventory (will be 0 or replenished)
        else:
            # Normal event: 95% success, 4% delay, 1% failure
            roll = rng.random()
            if roll < 0.95:
                event_type = "Success"
                delay_reason = None
                delay_hours = 0
            elif roll < 0.99:
                event_type = "Delay"
                reasons = list(_DELAY_REASONS.keys())
                weights = list(_DELAY_REASONS.values())
                delay_reason = str(rng.choice(reasons, p=weights))
                delay_hours = int(rng.integers(4, 72))
            else:
                event_type = "Failure"
                delay_reason = "System failure during randomization"
                delay_hours = 0

        event_rows.append({
            "subject_id": subj.subject_id,
            "site_id": subj.site_id,
            "event_date": rand_date,
            "event_type": event_type,
            "delay_reason": delay_reason,
            "delay_duration_hours": delay_hours,
        })

        # Decrement inventory for the relevant kit types
        arm = subj.arm_code
        if arm == "ARM_A":
            for kt in ["KIT_VEL", "KIT_CARBO", "KIT_PAC"]:
                if kt in inventory.get(subj.site_id, {}):
                    inventory[subj.site_id][kt] = max(0, inventory[subj.site_id][kt] - 1)
        else:
            kt = "KIT_STD"
            if kt in inventory.get(subj.site_id, {}):
                inventory[subj.site_id][kt] = max(0, inventory[subj.site_id][kt] - 1)

    # Generate kit inventory snapshots (biweekly)
    for site in sites:
        sid = site.site_id
        prof = ANOMALY_PROFILES.get(sid)
        snapshot_date = site.activation_date + timedelta(days=14)
        site_inv = inventory.get(sid, {})

        # Simulate inventory over time
        sim_inv: dict[str, int] = {}
        for kt in kit_type_ids:
            sim_inv[kt] = int(rng.integers(6, 11))  # initial stock

        # Count randomizations per site to model consumption
        site_subjects = [s for s in subjects if s.site_id == sid]
        subj_by_date: dict[date, int] = {}
        for s in site_subjects:
            subj_by_date[s.randomization_date] = subj_by_date.get(s.randomization_date, 0) + 1

        while snapshot_date <= SNAPSHOT_DATE:
            # Simulate consumption since last snapshot
            for kt in kit_type_ids:
                # Rough consumption: each randomization uses 1 kit of relevant type
                consumed = 0
                prev_snap = snapshot_date - timedelta(days=14)
                for d, cnt in subj_by_date.items():
                    if prev_snap < d <= snapshot_date:
                        consumed += cnt
                sim_inv[kt] = max(0, sim_inv[kt] - consumed // len(kit_type_ids))

                # Replenishment: if below reorder, add shipment
                if sim_inv[kt] <= 3:
                    sim_inv[kt] += int(rng.integers(5, 10))

                # Stockout override for anomaly sites
                if sid in stockout_windows:
                    for ws, we in stockout_windows[sid]:
                        if ws <= snapshot_date <= we:
                            sim_inv[kt] = 0

                # Chain 4: SITE-031 kits accumulate (low enrollment → expiry)
                if prof and prof.get("kit_expiry_count") and snapshot_date > STUDY_START + timedelta(days=270):
                    sim_inv[kt] = max(sim_inv[kt], int(rng.integers(8, 15)))

                is_below = sim_inv[kt] <= 3

                inv_rows.append({
                    "site_id": sid,
                    "kit_type_id": kt,
                    "snapshot_date": snapshot_date,
                    "quantity_on_hand": sim_inv[kt],
                    "reorder_level": 3,
                    "is_below_reorder": is_below,
                })

            snapshot_date += timedelta(days=14)

    # Generate depot shipments
    shipment_rows = _generate_shipments(rng, sites, subjects, stockout_windows)

    # Bulk insert
    session.bulk_insert_mappings(RandomizationEvent, event_rows)
    session.bulk_insert_mappings(KitInventory, inv_rows)
    session.bulk_insert_mappings(DepotShipment, shipment_rows)
    session.flush()

    return {
        "kit_inventory": len(inv_rows),
        "randomization_events": len(event_rows),
        "depot_shipments": len(shipment_rows),
    }


def _generate_shipments(
    rng: Generator, sites: list, subjects: list,
    stockout_windows: dict[str, list[tuple[date, date]]],
) -> list[dict]:
    """Generate depot shipments. Sites receive periodic replenishments."""
    rows: list[dict] = []
    kit_types = ["KIT_VEL", "KIT_CARBO", "KIT_PAC", "KIT_STD"]

    for site in sites:
        depot_id = _COUNTRY_DEPOT.get(site.country, "DEPOT_US")
        ship_days = _DEPOT_SHIPPING_DAYS.get(depot_id, 3)
        prof = ANOMALY_PROFILES.get(site.site_id)

        # Initial shipment at activation
        ship_date = site.activation_date - timedelta(days=ship_days + 2)
        for kt in kit_types:
            expected = ship_date + timedelta(days=ship_days)
            actual_arr = expected + timedelta(days=int(rng.integers(-1, 2)))
            rows.append({
                "depot_id": depot_id,
                "site_id": site.site_id,
                "kit_type_id": kt,
                "shipment_date": ship_date,
                "expected_arrival": expected,
                "actual_arrival": actual_arr,
                "kit_count": int(rng.integers(6, 11)),
                "status": "Delivered",
                "delay_reason": None,
            })

        # Periodic replenishments every 6-10 weeks
        next_ship = site.activation_date + timedelta(weeks=int(rng.integers(6, 11)))
        while next_ship <= SNAPSHOT_DATE:
            kt = str(rng.choice(kit_types))
            expected = next_ship + timedelta(days=ship_days)
            actual_arr = expected

            # 5% delayed
            is_delayed = rng.random() < 0.05
            delay_reason = None
            status = "Delivered"

            # Stockout-related shipment delays
            if site.site_id in stockout_windows:
                for ws, we in stockout_windows[site.site_id]:
                    if ws - timedelta(days=10) <= next_ship <= we:
                        is_delayed = True
                        # Find reason from profile
                        if prof:
                            for ep in prof.get("stockout_episodes", []):
                                if ep["start"] == ws:
                                    delay_reason = ep["reason"]
                                    break

            if is_delayed:
                extra_days = int(rng.integers(3, 8))
                actual_arr = expected + timedelta(days=extra_days)
                if delay_reason is None:
                    delay_reason = str(rng.choice([
                        "Customs clearance delay", "Weather disruption",
                        "Carrier logistics issue", "Documentation error",
                    ]))
                status = "Delayed" if actual_arr > SNAPSHOT_DATE else "Delivered"

            if actual_arr > SNAPSHOT_DATE:
                status = "In-Transit"
                actual_arr = None

            rows.append({
                "depot_id": depot_id,
                "site_id": site.site_id,
                "kit_type_id": kt,
                "shipment_date": next_ship,
                "expected_arrival": expected,
                "actual_arrival": actual_arr,
                "kit_count": int(rng.integers(4, 10)),
                "status": status,
                "delay_reason": delay_reason if is_delayed else None,
            })

            next_ship += timedelta(weeks=int(rng.integers(6, 11)))

    return rows
