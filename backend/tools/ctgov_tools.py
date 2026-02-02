"""ClinicalTrials.gov API v2 tool for competitive intelligence."""

import asyncio
import logging

import httpx

from backend.tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)

CTGOV_API_BASE = "https://clinicaltrials.gov/api/v2/studies"

# Our own trial — filter from results to avoid self-matches
OWN_TRIAL_NCT = "NCT02264990"


class CompetingTrialSearchTool(BaseTool):
    name = "competing_trial_search"
    description = (
        "Searches ClinicalTrials.gov for competing clinical trials near a geographic location. "
        "Returns real external trials that may be competing for patient enrollment. "
        "Args: condition (str, e.g. 'Non-Small Cell Lung Cancer'), "
        "location_terms (str, city/state/country for location filter, e.g. 'Springdale, Arkansas'), "
        "distance (str, distance radius e.g. '100mi'), "
        "status (str, default 'RECRUITING|ACTIVE_NOT_RECRUITING')."
    )

    async def execute(self, db_session, **kwargs) -> ToolResult:
        condition = kwargs.get("condition", "Non-Small Cell Lung Cancer")
        location_terms = kwargs.get("location_terms", "")
        distance = kwargs.get("distance", "100mi")
        status = kwargs.get("status", "RECRUITING|ACTIVE_NOT_RECRUITING")

        if not location_terms:
            return ToolResult(
                tool_name=self.name,
                success=False,
                error="location_terms is required (e.g. 'Springdale, Arkansas')",
            )

        params = {
            "query.cond": condition,
            "query.locn": location_terms,
            "filter.overallStatus": status,
            "pageSize": 20,
            "fields": (
                "NCTId,BriefTitle,OverallStatus,Phase,LeadSponsorName,"
                "StartDate,PrimaryCompletionDate,EnrollmentCount,"
                "LocationFacility,LocationCity,LocationState,LocationCountry"
            ),
        }

        data = await self._fetch_with_retry(params)
        if data is None:
            return ToolResult(
                tool_name=self.name,
                success=False,
                error="ClinicalTrials.gov API request failed after retries",
            )

        studies = self._parse_studies(data)
        return ToolResult(
            tool_name=self.name,
            success=True,
            data=studies,
            row_count=len(studies),
        )

    async def _fetch_with_retry(self, params: dict, max_retries: int = 1) -> dict | None:
        """Fetch from ClinicalTrials.gov with retry on 429."""
        for attempt in range(max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(CTGOV_API_BASE, params=params)
                    if resp.status_code == 200:
                        return resp.json()
                    if resp.status_code == 429 and attempt < max_retries:
                        logger.warning("ClinicalTrials.gov rate limited, retrying after backoff")
                        await asyncio.sleep(2)
                        continue
                    logger.error("ClinicalTrials.gov API returned %d: %s", resp.status_code, resp.text[:200])
                    return None
            except httpx.TimeoutException:
                logger.error("ClinicalTrials.gov API timeout (attempt %d)", attempt + 1)
                if attempt < max_retries:
                    await asyncio.sleep(2)
                    continue
                return None
            except Exception as e:
                logger.error("ClinicalTrials.gov API error: %s", e)
                return None
        return None

    def _parse_studies(self, data: dict) -> list[dict]:
        """Extract relevant fields from API v2 response."""
        studies = []
        for study in data.get("studies", []):
            proto = study.get("protocolSection", {})
            ident = proto.get("identificationModule", {})
            status_mod = proto.get("statusModule", {})
            design = proto.get("designModule", {})
            sponsor_mod = proto.get("sponsorCollaboratorsModule", {})
            contacts_loc = proto.get("contactsLocationsModule", {})

            nct_id = ident.get("nctId", "")
            if nct_id == OWN_TRIAL_NCT:
                continue

            # Extract locations
            locations = []
            for loc in contacts_loc.get("locations", []):
                locations.append({
                    "facility": loc.get("facility", ""),
                    "city": loc.get("city", ""),
                    "state": loc.get("state", ""),
                    "country": loc.get("country", ""),
                })

            # Extract phase
            phases = design.get("phases", [])
            phase_str = ", ".join(phases) if phases else "N/A"

            # Extract sponsor
            lead_sponsor = sponsor_mod.get("leadSponsor", {})

            # Extract enrollment
            enrollment_info = design.get("enrollmentInfo", {})

            studies.append({
                "nct_id": nct_id,
                "title": ident.get("briefTitle", ""),
                "sponsor": lead_sponsor.get("name", ""),
                "phase": phase_str,
                "status": status_mod.get("overallStatus", ""),
                "start_date": status_mod.get("startDateStruct", {}).get("date", ""),
                "primary_completion_date": status_mod.get("primaryCompletionDateStruct", {}).get("date", ""),
                "enrollment": enrollment_info.get("count"),
                "locations_near_site": locations[:5],
            })

        return studies
