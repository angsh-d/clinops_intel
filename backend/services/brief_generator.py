"""Site Intelligence Brief Generator: synthesizes per-site briefs from proactive scan findings."""

import json
import logging
from collections import defaultdict

from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.llm.failover import FailoverLLMClient
from backend.llm.utils import parse_llm_json
from backend.models.governance import AgentFinding, ProactiveScan, SiteIntelligenceBrief
from backend.prompts.manager import get_prompt_manager

logger = logging.getLogger(__name__)


class SiteIntelligenceBriefGenerator:
    """Generates per-site intelligence briefs from proactive scan findings."""

    async def generate_briefs(
        self,
        scan_id: str,
        findings: list[AgentFinding],
        db: Session,
    ) -> list[SiteIntelligenceBrief]:
        """Group findings by site, synthesize per-site briefs via LLM."""
        # Group findings by site_id
        by_site: dict[str, list[AgentFinding]] = defaultdict(list)
        for f in findings:
            site_key = f.site_id or "STUDY"
            by_site[site_key].append(f)

        if not by_site:
            return []

        settings = get_settings()
        llm = FailoverLLMClient(settings)
        prompts = get_prompt_manager()
        briefs = []
        failed_sites = []

        for site_id, site_findings in by_site.items():
            try:
                brief = await self._generate_one_brief(
                    scan_id, site_id, site_findings, llm, prompts, db
                )
                if brief:
                    briefs.append(brief)
            except Exception as e:
                logger.error("Brief generation failed for site %s: %s", site_id, e)
                failed_sites.append({"site_id": site_id, "error": str(e)})

        if failed_sites:
            logger.warning(
                "Brief generation failed for %d/%d sites in scan %s: %s",
                len(failed_sites), len(by_site), scan_id, failed_sites,
            )
        logger.info("Generated %d site intelligence briefs for scan %s", len(briefs), scan_id)
        return briefs

    async def _generate_one_brief(
        self,
        scan_id: str,
        site_id: str,
        findings: list[AgentFinding],
        llm,
        prompts,
        db: Session,
    ) -> SiteIntelligenceBrief | None:
        """Generate a single site intelligence brief."""
        # Format findings by agent for the prompt
        findings_by_agent: dict[str, list[dict]] = defaultdict(list)
        for f in findings:
            findings_by_agent[f.agent_id].append({
                "finding_type": f.finding_type,
                "severity": f.severity,
                "summary": f.summary,
                "confidence": f.confidence,
                "detail": f.detail,
            })

        findings_json = json.dumps(findings_by_agent, default=str)

        # Extract investigation steps from findings BEFORE generation
        # so we can pass them to the prompt as context
        all_investigation_steps = self._extract_investigation_steps(findings)
        
        # Build available tools context for the prompt
        available_tools = self._format_available_tools(all_investigation_steps)
        tool_registry = self._get_tool_registry()

        prompt = prompts.render(
            "proactive_site_brief",
            site_id=site_id,
            findings_by_agent=findings_json,
            findings_count=str(len(findings)),
            available_tools=available_tools,
            tool_registry=tool_registry,
        )

        response = await llm.generate_structured(
            prompt,
            system="You are a clinical operations intelligence analyst. Respond with valid JSON only.",
        )

        try:
            parsed = parse_llm_json(response.text)
        except (json.JSONDecodeError, ValueError) as e:
            logger.error("Brief LLM parse failed for site %s: %s", site_id, e)
            return None

        # Extract contributing agents from findings
        agent_map = {}
        for f in findings:
            if f.agent_id and f.agent_id not in agent_map:
                agent_map[f.agent_id] = {
                    "name": f.agent_id,
                    "role": self._get_agent_role(f.agent_id),
                }
        contributing_agents = list(agent_map.values()) if agent_map else None

        # Truncate investigation_steps for display (all_investigation_steps already extracted above)
        investigation_steps = all_investigation_steps[:10] if all_investigation_steps else None

        # Extract key_risks from nested risk_summary structure
        risk_summary = parsed.get("risk_summary", {})
        key_risks = risk_summary.get("key_risks") if isinstance(risk_summary, dict) else None

        # Step 1: Deterministic pre-validation to check for obvious issues
        validation_issues = []
        if key_risks and all_investigation_steps:
            validation_issues = self._deterministic_validation(key_risks, all_investigation_steps)
        
        # Step 2: LLM reflection pass if there are validation issues
        if validation_issues and key_risks:
            logger.info("Found %d validation issues for site %s, running reflection pass", len(validation_issues), site_id)
            reflected_risks = await self._reflection_pass(
                key_risks, all_investigation_steps, llm, prompts, available_tools
            )
            if reflected_risks:
                key_risks = reflected_risks
                risk_summary["key_risks"] = key_risks

        # Step 3: Final data grounding validation
        if key_risks and all_investigation_steps:
            key_risks = self._validate_data_grounding(key_risks, all_investigation_steps)

        brief = SiteIntelligenceBrief(
            scan_id=scan_id,
            site_id=site_id,
            risk_summary=risk_summary,
            key_risks=key_risks,
            vendor_accountability=parsed.get("vendor_accountability"),
            cross_domain_correlations=parsed.get("cross_domain_correlations"),
            recommended_actions=parsed.get("recommended_actions"),
            trend_indicator=parsed.get("trend_indicator", "stable"),
            agent="proactive_briefing_agent",
            contributing_agents=contributing_agents,
            investigation_steps=investigation_steps,
        )
        db.add(brief)
        db.commit()
        db.refresh(brief)
        logger.info("Created brief id=%d for site %s (scan %s)", brief.id, site_id, scan_id)
        return brief

    def _get_agent_role(self, agent_id: str) -> str:
        """Get human-readable role description for an agent."""
        roles = {
            "enrollment_agent": "Enrollment & Recruitment Analysis",
            "data_quality_agent": "Data Quality Monitoring",
            "financial_agent": "Financial & Budget Analysis",
            "data_integrity_agent": "Data Integrity & Fraud Detection",
            "vendor_agent": "Vendor Performance Tracking",
            "site_health_agent": "Site Health Assessment",
            "phantom_compliance": "Compliance & Fraud Detection",
        }
        return roles.get(agent_id, "Analysis & Investigation")

    def _extract_investigation_steps(self, findings: list[AgentFinding]) -> list[dict]:
        """Extract all investigation steps from findings reasoning traces."""
        all_steps = []
        seen_steps = set()
        for f in findings:
            if f.reasoning_trace and isinstance(f.reasoning_trace, dict):
                steps = f.reasoning_trace.get("steps", [])
                for step in steps:
                    step_key = (step.get("tool", ""), step.get("step", "")[:50])
                    if step_key not in seen_steps:
                        seen_steps.add(step_key)
                        all_steps.append({
                            "icon": step.get("icon", "search"),
                            "step": step.get("step", "Analyzed data"),
                            "tool": step.get("tool"),
                            "success": step.get("success", True),
                            "row_count": step.get("row_count"),
                        })
        return all_steps

    def _format_available_tools(self, investigation_steps: list[dict]) -> str:
        """Format investigation steps as context for the LLM prompt."""
        if not investigation_steps:
            return "No tools were called during investigation. Mark all claims as inferences."
        
        lines = []
        for step in investigation_steps:
            tool = step.get("tool", "unknown")
            row_count = step.get("row_count", 0) or 0
            success = step.get("success", False)
            status = "✓" if success else "✗"
            lines.append(f"  - {status} {tool}: {row_count} rows returned")
        
        return "\n".join(lines)

    def _get_tool_registry(self) -> str:
        """Return list of valid tool names the LLM can cite."""
        tools = [
            "screening_funnel - Enrollment funnel metrics (screen, consent, randomize)",
            "enrollment_trajectory - Projected enrollment vs actual over time",
            "site_performance_summary - Multi-dimensional site health scores",
            "burn_rate_projection - Monthly spending vs budget projections",
            "budget_variance_analysis - Variance between planned and actual spend",
            "cost_per_patient_analysis - Per-patient costs by category",
            "change_order_impact - Impact of protocol amendments on budget",
            "financial_impact_of_delays - Cost impact of enrollment delays",
            "query_burden - Open/resolved query counts and aging",
            "data_completeness - CRF field completion rates",
            "edit_check_violations - Protocol deviations and edit check failures",
            "cra_assignment_history - CRA assignments and transitions",
            "monitoring_visit_history - On-site/remote visit records",
            "weekday_entry_pattern - Detects suspicious batch entry patterns",
            "entry_date_clustering - Detects backfill/batch data entry",
            "cra_oversight_gap - Periods without monitoring coverage",
            "cra_portfolio_analysis - CRA finding patterns across sites",
            "correction_provenance - Pre-emptive vs prompted corrections",
            "screening_narrative_duplication - Copy-paste detection in narratives",
            "cross_domain_consistency - Cross-checks metrics across domains",
            "inference - Use for logical conclusions derived from other data",
        ]
        return "\n".join(f"  - {t}" for t in tools)

    def _deterministic_validation(
        self, key_risks: list[dict], investigation_steps: list[dict]
    ) -> list[str]:
        """Perform deterministic checks on causal chain claims.
        
        Returns a list of validation issues found.
        """
        issues = []
        
        # Build set of tools that were actually called
        called_tools = set()
        tool_row_counts = {}
        for step in investigation_steps:
            tool_name = step.get("tool")
            if tool_name:
                normalized = tool_name.strip().lower()
                called_tools.add(normalized)
                row_count = step.get("row_count", 0) or 0
                if normalized not in tool_row_counts or row_count > tool_row_counts[normalized]:
                    tool_row_counts[normalized] = row_count
        
        # Valid tool names from registry (normalized)
        valid_tools = {
            "screening_funnel", "enrollment_trajectory", "site_performance_summary",
            "burn_rate_projection", "budget_variance_analysis", "cost_per_patient_analysis",
            "change_order_impact", "financial_impact_of_delays", "query_burden",
            "data_completeness", "edit_check_violations", "cra_assignment_history",
            "monitoring_visit_history", "weekday_entry_pattern", "entry_date_clustering",
            "cra_oversight_gap", "cra_portfolio_analysis", "correction_provenance",
            "screening_narrative_duplication", "cross_domain_consistency",
            "vendor_kpi_analysis", "vendor_performance_summary",
            "inference", "derived",
        }
        
        for risk_idx, risk in enumerate(key_risks):
            causal_chain = risk.get("causal_chain_explained", [])
            for step_idx, step in enumerate(causal_chain):
                data_source = step.get("data_source", {})
                if not isinstance(data_source, dict):
                    issues.append(f"Risk {risk_idx+1}, Step {step_idx+1}: Missing data_source")
                    continue
                    
                cited_tool = data_source.get("tool", "").strip().lower()
                cited_rows = data_source.get("row_count", 0) or 0
                
                # Skip inferences
                if cited_tool in ("inference", "derived", ""):
                    continue
                
                # Check 1: Is this a valid tool name from the registry?
                if cited_tool not in valid_tools:
                    issues.append(
                        f"Risk {risk_idx+1}, Step {step_idx+1}: "
                        f"Tool '{cited_tool}' is not in the tool registry"
                    )
                    continue
                
                # Check 2: Was this tool actually called?
                if cited_tool not in called_tools:
                    issues.append(
                        f"Risk {risk_idx+1}, Step {step_idx+1}: "
                        f"Tool '{cited_tool}' was never called during investigation"
                    )
                    continue
                
                # Check 3: Is the row count plausible (within 20%)?
                actual_rows = tool_row_counts.get(cited_tool, 0)
                if actual_rows > 0 and cited_rows > 0:
                    variance = abs(cited_rows - actual_rows) / actual_rows
                    if variance > 0.2:
                        issues.append(
                            f"Risk {risk_idx+1}, Step {step_idx+1}: "
                            f"Cited {cited_rows} rows but tool returned {actual_rows}"
                        )
        
        return issues

    async def _reflection_pass(
        self,
        key_risks: list[dict],
        investigation_steps: list[dict],
        llm,
        prompts,
        available_tools: str,
    ) -> list[dict] | None:
        """Run LLM reflection to revise ungrounded claims.
        
        This is a second LLM pass that reviews the draft and fixes grounding issues.
        """
        try:
            draft_json = json.dumps({"key_risks": key_risks}, default=str)
            
            reflection_prompt = prompts.render(
                "brief_reflection",
                draft_brief=draft_json,
                available_tools=available_tools,
            )
            
            response = await llm.generate_structured(
                reflection_prompt,
                system="You are a data validation expert. Review claims against actual data. Respond with valid JSON only.",
            )
            
            parsed = parse_llm_json(response.text)
            
            # Log validation summary
            summary = parsed.get("validation_summary", {})
            if summary:
                logger.info(
                    "Reflection pass: %d/%d claims verified, issues: %s",
                    summary.get("verified_claims", 0),
                    summary.get("total_claims", 0),
                    summary.get("issues_found", [])[:3],
                )
            
            revised_risks = parsed.get("revised_key_risks", [])
            return revised_risks if revised_risks else None
            
        except Exception as e:
            logger.warning("Reflection pass failed: %s", e)
            return None

    def _validate_data_grounding(
        self, key_risks: list[dict], investigation_steps: list[dict]
    ) -> list[dict]:
        """Validate causal chain claims against actual tool outputs.
        
        Adds 'grounded' boolean to each causal chain step:
        - True: Tool was called and returned data (row_count > 0)
        - False: Tool wasn't called, or returned 0 rows, or is an inference
        
        Also adds 'grounding_issue' string when there's a mismatch.
        """
        # Build map of tool names to their actual results (normalized to lowercase)
        tool_results = {}
        for step in investigation_steps:
            tool_name = step.get("tool")
            if tool_name:
                normalized_tool = tool_name.strip().lower()
                row_count = step.get("row_count", 0) or 0
                success = step.get("success", False)
                # Store the best result for each tool (highest row count)
                if normalized_tool not in tool_results or row_count > tool_results[normalized_tool]["row_count"]:
                    tool_results[normalized_tool] = {
                        "row_count": row_count,
                        "success": success,
                    }

        validated_risks = []
        for risk in key_risks:
            causal_chain = risk.get("causal_chain_explained", [])
            validated_chain = []
            
            for step in causal_chain:
                validated_step = dict(step)
                data_source = step.get("data_source", {})
                
                if isinstance(data_source, dict) and data_source:
                    cited_tool = data_source.get("tool", "").strip().lower()
                    cited_row_count = data_source.get("row_count") or 0
                    
                    # Determine grounding status
                    if not cited_tool:
                        # Empty tool field
                        validated_step["grounded"] = False
                        validated_step["grounding_type"] = "missing"
                        validated_step["grounding_issue"] = "No tool specified in data source"
                    elif cited_tool == "inference" or cited_tool == "derived":
                        # Inferences are explicitly marked as such (not unverified)
                        validated_step["grounded"] = False
                        validated_step["grounding_type"] = "inference"
                        # Default confidence for inferences
                        if "confidence" not in validated_step:
                            validated_step["confidence"] = 0.6
                            validated_step["confidence_reason"] = "Derived from available data"
                    elif cited_tool in tool_results:
                        actual = tool_results[cited_tool]
                        if actual["row_count"] > 0 and actual["success"]:
                            validated_step["grounded"] = True
                            validated_step["grounding_type"] = "data"
                            # Default high confidence for verified data
                            if "confidence" not in validated_step:
                                validated_step["confidence"] = 0.9
                                validated_step["confidence_reason"] = "Verified against tool output"
                            # Check for significant row count mismatch (allow 20% variance)
                            if cited_row_count > 0:
                                variance = abs(cited_row_count - actual["row_count"]) / max(actual["row_count"], 1)
                                if variance > 0.2:
                                    validated_step["grounding_issue"] = (
                                        f"Cited {cited_row_count} rows, tool returned {actual['row_count']}"
                                    )
                                    validated_step["confidence"] = 0.7
                        else:
                            validated_step["grounded"] = False
                            validated_step["grounding_type"] = "unverified"
                            validated_step["grounding_issue"] = (
                                f"Tool {cited_tool} returned 0 rows but claim cites data"
                            )
                            if "confidence" not in validated_step:
                                validated_step["confidence"] = 0.3
                                validated_step["confidence_reason"] = "Tool returned no data"
                    else:
                        # Tool was cited but never actually called
                        validated_step["grounded"] = False
                        validated_step["grounding_type"] = "unverified"
                        validated_step["grounding_issue"] = (
                            f"Tool '{cited_tool}' was not called during investigation"
                        )
                        if "confidence" not in validated_step:
                            validated_step["confidence"] = 0.2
                            validated_step["confidence_reason"] = "Tool not called during investigation"
                else:
                    # No data_source provided (legacy format)
                    validated_step["grounded"] = False
                    validated_step["grounding_type"] = "missing"
                    validated_step["grounding_issue"] = "No data source citation provided"
                    if "confidence" not in validated_step:
                        validated_step["confidence"] = 0.1
                        validated_step["confidence_reason"] = "No data source citation"
                
                validated_chain.append(validated_step)
            
            risk["causal_chain_explained"] = validated_chain
            validated_risks.append(risk)
        
        return validated_risks

    async def generate_study_synthesis(
        self,
        scan_id: str,
        findings: list[AgentFinding],
        briefs: list[SiteIntelligenceBrief],
        db: Session,
    ) -> dict | None:
        """Generate study-wide cross-domain synthesis from all findings and briefs."""
        if not findings:
            return None

        settings = get_settings()
        llm = FailoverLLMClient(settings)
        prompts = get_prompt_manager()

        # Group findings by agent_id
        findings_by_agent: dict[str, list[dict]] = defaultdict(list)
        for f in findings:
            findings_by_agent[f.agent_id or "unknown"].append({
                "site_id": f.site_id,
                "severity": f.severity,
                "summary": f.summary,
                "confidence": f.confidence,
            })

        # Summarize briefs
        briefs_summary = []
        for b in briefs:
            risk = b.risk_summary or {}
            briefs_summary.append({
                "site_id": b.site_id,
                "risk_level": risk.get("overall_risk", "unknown"),
                "headline": risk.get("headline"),
                "cross_domain_correlations": b.cross_domain_correlations,
                "trend": b.trend_indicator,
            })

        prompt = prompts.render(
            "proactive_study_synthesis",
            findings_by_agent=json.dumps(findings_by_agent, default=str),
            site_briefs_summary=json.dumps(briefs_summary, default=str),
        )

        try:
            response = await llm.generate_structured(
                prompt,
                system="You are a clinical operations intelligence analyst. Respond with valid JSON only.",
            )
            parsed = parse_llm_json(response.text)
        except Exception as e:
            logger.error("Study synthesis LLM call failed for scan %s: %s", scan_id, e)
            return None

        # Store in ProactiveScan record
        scan = db.query(ProactiveScan).filter_by(scan_id=scan_id).first()
        if scan:
            scan.study_synthesis = parsed
            db.commit()
            logger.info("Stored study synthesis for scan %s", scan_id)

        return parsed
