"""ClinicalTrials.gov tools powered by BioMCP for competitive intelligence."""

import json
import logging
import re

from backend.tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)

BIOMCP_AVAILABLE = False
try:
    from biomcp.trials.search import (
        search_trials,
        TrialQuery,
        RecruitingStatus,
        TrialPhase,
    )
    from biomcp.trials.getter import get_trial, Module
    BIOMCP_AVAILABLE = True
except ImportError:
    logger.warning("biomcp.trials not available - ClinicalTrials.gov tools disabled")
    search_trials = None
    TrialQuery = None
    RecruitingStatus = None
    TrialPhase = None
    get_trial = None
    Module = None

# Our own trial — filter from results to avoid self-matches
OWN_TRIAL_NCT = "NCT02264990"

# Fields to request from ClinicalTrials.gov CSV API (includes Sponsor)
_SEARCH_FIELDS = [
    "NCT Number", "Study Title", "Study URL", "Study Status",
    "Conditions", "Interventions", "Sponsor", "Phases",
    "Enrollment", "Start Date", "Completion Date",
]

# Map user-friendly phase strings to BioMCP enum (only if available)
_PHASE_MAP = {}
if BIOMCP_AVAILABLE and TrialPhase is not None:
    _PHASE_MAP = {
        "1": TrialPhase.PHASE1,
        "2": TrialPhase.PHASE2,
        "3": TrialPhase.PHASE3,
        "4": TrialPhase.PHASE4,
        "phase1": TrialPhase.PHASE1,
        "phase2": TrialPhase.PHASE2,
        "phase3": TrialPhase.PHASE3,
        "phase4": TrialPhase.PHASE4,
        "PHASE1": TrialPhase.PHASE1,
        "PHASE2": TrialPhase.PHASE2,
        "PHASE3": TrialPhase.PHASE3,
        "PHASE4": TrialPhase.PHASE4,
    }


def _parse_phase(phase_str):
    """Convert user phase string to BioMCP TrialPhase enum if available."""
    if not BIOMCP_AVAILABLE or not phase_str:
        return None
    return _PHASE_MAP.get(phase_str)


def _parse_distance(distance):
    """Convert distance to int miles."""
    if isinstance(distance, int):
        return distance
    if isinstance(distance, str):
        numeric = re.sub(r"[^\d]", "", distance)
    else:
        numeric = str(distance)
    try:
        return int(numeric)
    except ValueError:
        return 50  # default


# Only define actual tool classes when biomcp is available
if BIOMCP_AVAILABLE:
    class CompetingTrialSearchTool(BaseTool):
        name = "competing_trial_search"
        description = (
            "Searches ClinicalTrials.gov for competing clinical trials using BioMCP. "
            "Supports geo-distance search (lat/lon + radius), condition synonym expansion, "
            "and automatic pagination. Returns external trials that may compete for enrollment. "
            "Args: condition (str, e.g. 'Non-Small Cell Lung Cancer'), "
            "lat (float, latitude for geo search), lon (float, longitude for geo search), "
            "distance (int or str, radius in miles, default 50, e.g. 50 or '100mi'), "
            "location_terms (str, text search fallback when lat/lon unavailable — "
            "NOTE: this is a full-text search, not a geo filter; prefer lat/lon for accurate results), "
            "phase (str, e.g. 'PHASE3'), "
            "status (str, 'OPEN' or 'CLOSED' or 'ANY', default 'OPEN'), "
            "intervention (str, optional drug/intervention name), "
            "page_size (int, results per page, default 40)."
        )

        async def execute(self, db_session, **kwargs) -> ToolResult:
            condition = kwargs.get("condition", "Non-Small Cell Lung Cancer")
            lat = kwargs.get("lat")
            lon = kwargs.get("lon")
            location_terms = kwargs.get("location_terms", "")
            distance = kwargs.get("distance", 50)
            phase_str = kwargs.get("phase")
            status_str = kwargs.get("status", "OPEN")
            intervention = kwargs.get("intervention")
            page_size = kwargs.get("page_size", 40)

            # Build TrialQuery
            query_params = {
                "conditions": [condition],
                "expand_synonyms": True,
                "page_size": int(page_size),
                "return_fields": _SEARCH_FIELDS,
            }

            # Geo-distance search (preferred over text location)
            if lat is not None and lon is not None:
                query_params["lat"] = float(lat)
                query_params["long"] = float(lon)
                query_params["distance"] = _parse_distance(distance)
            elif location_terms:
                # Full-text search fallback — matches location_terms anywhere
                # in the study record, not just in location fields.
                query_params["terms"] = [location_terms]

            # Phase filter
            phase = _parse_phase(phase_str)
            if phase:
                query_params["phase"] = phase

            # Status filter
            status_map = {
                "OPEN": RecruitingStatus.OPEN,
                "CLOSED": RecruitingStatus.CLOSED,
                "ANY": RecruitingStatus.ANY,
            }
            query_params["recruiting_status"] = status_map.get(
                status_str.upper(), RecruitingStatus.OPEN
            )

            # Intervention filter
            if intervention:
                query_params["interventions"] = [intervention]

            try:
                query = TrialQuery(**query_params)
                result_json = await search_trials(query, output_json=True)
                data = json.loads(result_json)
            except Exception as e:
                logger.error("BioMCP trial search failed: %s", e, exc_info=True)
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    error=f"ClinicalTrials.gov search failed: {e}",
                )

            # BioMCP returns a dict on error, a list on success
            if isinstance(data, dict) and "error" in data:
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    error=data["error"],
                )

            if not isinstance(data, list):
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    error=f"Unexpected response type: {type(data).__name__}",
                )

            studies = self._parse_studies(data)
            return ToolResult(
                tool_name=self.name,
                success=True,
                data=studies,
                row_count=len(studies),
            )

        def _parse_studies(self, rows: list[dict]) -> list[dict]:
            """Extract relevant fields from BioMCP CSV-style response rows."""
            studies = []
            for row in rows:
                nct_id = row.get("NCT Number", "")
                if nct_id == OWN_TRIAL_NCT:
                    continue
                studies.append({
                    "nct_id": nct_id,
                    "title": row.get("Study Title", ""),
                    "sponsor": row.get("Sponsor", ""),
                    "phase": row.get("Phases", "N/A"),
                    "status": row.get("Study Status", ""),
                    "conditions": row.get("Conditions", ""),
                    "interventions": row.get("Interventions", ""),
                    "start_date": row.get("Start Date", ""),
                    "primary_completion_date": row.get("Completion Date", ""),
                    "enrollment": row.get("Enrollment"),
                    "study_url": row.get("Study URL", ""),
                })
            return studies


    class TrialDetailTool(BaseTool):
        name = "trial_detail"
        description = (
            "Fetches detailed information for a specific clinical trial by NCT ID. "
            "Can retrieve protocol/eligibility, locations with contact info, "
            "published references, or outcome measures. "
            "Use after competing_trial_search to deep-dive on specific competing trials. "
            "Args: nct_id (str, required, e.g. 'NCT04280705'), "
            "module (str, one of 'protocol', 'locations', 'references', 'outcomes', 'all', default 'protocol')."
        )

        _MODULE_MAP = {
            "protocol": Module.PROTOCOL,
            "locations": Module.LOCATIONS,
            "references": Module.REFERENCES,
            "outcomes": Module.OUTCOMES,
            "all": Module.ALL,
        }

        async def execute(self, db_session, **kwargs) -> ToolResult:
            nct_id = kwargs.get("nct_id")
            if not nct_id:
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    error="nct_id is required (e.g. 'NCT04280705')",
                )

            module_str = kwargs.get("module", "protocol").lower()
            module = self._MODULE_MAP.get(module_str, Module.PROTOCOL)

            try:
                result_json = await get_trial(nct_id, module=module, output_json=True)
                data = json.loads(result_json)
            except Exception as e:
                logger.error("BioMCP trial detail fetch failed: %s", e, exc_info=True)
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    error=f"Trial detail fetch failed for {nct_id}: {e}",
                )

            if isinstance(data, dict) and "error" in data:
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    error=data["error"],
                )

            return ToolResult(
                tool_name=self.name,
                success=True,
                data=data,
                row_count=1,
            )

else:
    # Stub classes when biomcp is not available
    class CompetingTrialSearchTool(BaseTool):
        name = "competing_trial_search"
        description = "ClinicalTrials.gov search (requires biomcp package)"

        async def execute(self, db_session, **kwargs) -> ToolResult:
            return ToolResult(
                tool_name=self.name,
                success=False,
                error="ClinicalTrials.gov tools unavailable - biomcp package not installed",
            )


    class TrialDetailTool(BaseTool):
        name = "trial_detail"
        description = "ClinicalTrials.gov trial details (requires biomcp package)"

        async def execute(self, db_session, **kwargs) -> ToolResult:
            return ToolResult(
                tool_name=self.name,
                success=False,
                error="ClinicalTrials.gov tools unavailable - biomcp package not installed",
            )
