# User Acceptance Test Inventory — Clinical Operations Intelligence System

**Total automated tests: 113** | **Agentic UAT scenarios: 49** | **13 test files**

---

## Part 1: Agentic Investigation UAT Cases (49 tests)

---

### UAT Group 1: The System Uses Real Clinical Data in Its Reasoning (3 cases)

**UAT-1.1: The system bases its reasoning on actual site data, not generic assumptions**

**Scenario:** A Clinical Data Manager wants to verify that the AI assistant is genuinely analyzing their trial's data, not producing canned responses.
**Given:** Site 003 has an average eCRF entry delay of 12.4 days, and Site 005 has an average delay of 2.1 days.
**When:** The user asks "Which sites have data quality issues?"
**Then:** The system's analysis reasoning references Site 003 and its 12.4-day delay, as well as Site 005 and its 2.1-day delay — confirming it used the actual clinical data to form its conclusions.

**UAT-1.2: The system's investigation plan references the specific issues it identified**

**Scenario:** A Clinical Data Manager wants to confirm that the system's investigation plan is tailored to the problems it found, not a generic checklist.
**Given:** The system's initial analysis identified the hypothesis "Site 003 has severe entry lag (12.4 days mean)."
**When:** The user asks "Investigate Site 003."
**Then:** The investigation plan references Site 003 and the 12.4-day delay from its hypothesis, and lists the relevant analyses it intends to run — proving the plan is driven by the data, not a template.

**UAT-1.3: The system's final review includes the results of every analysis it ran**

**Scenario:** An auditor wants to confirm the system reviewed all its own investigation results before drawing conclusions.
**Given:** The system ran an eCRF entry delay analysis (finding a 12.4-day average at Site 003) and a data correction rate analysis (finding an 18% correction rate at Site 003).
**When:** The user asks "Check Site 003."
**Then:** The system's final review step references both the entry delay analysis and the data correction analysis for Site 003 — proving all investigation results were considered before the conclusion was formed.

---

### UAT Group 2: The System Deepens Its Investigation When Initial Analysis Is Incomplete (3 cases)

**UAT-2.1: An incomplete first pass triggers a second round of investigation**

**Scenario:** A Clinical Operations Lead wants assurance that the system does not stop prematurely when its first analysis round leaves questions unanswered.
**Given:** After the first investigation pass, the system determines its analysis is incomplete (e.g., "Need correction analysis for Site 003"). After the second pass, it determines the analysis is complete.
**When:** The user asks "Investigate Site 003."
**Then:** The system performs two full investigation cycles. The investigation audit log shows two separate data-gathering steps, confirming the system re-examined the data to fill the gaps.

**UAT-2.2: Findings from earlier investigation rounds are retained, not discarded**

**Scenario:** A Clinical Data Manager wants to confirm that the system remembers what it found in earlier investigation rounds.
**Given:** The system runs two investigation rounds, each analyzing eCRF entry delays and data correction rates for Site 003. The first round's review determines more analysis is needed.
**When:** The system completes both investigation rounds.
**Then:** The second round's final review contains results from both the first and second rounds — proving the system accumulated all findings rather than starting fresh.

**UAT-2.3: The system stops after a maximum number of investigation rounds and reports partial findings**

**Scenario:** A Clinical Operations Lead wants to know the system will not run indefinitely if it cannot fully resolve a question.
**Given:** The system is configured with a maximum of 3 investigation rounds. After each round, the system determines more analysis is still needed.
**When:** The user asks a question that cannot be fully resolved.
**Then:** The system stops after exactly 3 investigation rounds. It still presents its partial findings (including Site 003 with a note like "Still investigating," confidence 0.4) and assigns a Medium severity — rather than crashing or running forever.

---

### UAT Group 3: The System Continues Operating When a Data Source Is Unavailable (3 cases)

**UAT-3.1: One data source fails, but the system still completes its analysis using the remaining sources**

**Scenario:** A Clinical Data Manager runs an analysis while one of the clinical databases is temporarily offline.
**Given:** The eCRF entry delay data source is returning a "database connection timeout" error. All other data quality data sources (outstanding queries, data corrections, CRA staffing history, monitoring visits) are working normally.
**When:** The user asks any data quality question.
**Then:** The system completes its analysis using the four available data sources. The eCRF entry delay section is empty, but the outstanding query section and others contain data. The system does not crash.

**UAT-3.2: When an analysis step fails mid-investigation, the failure details are included in the final review**

**Scenario:** A Clinical Operations Lead wants to know whether the system transparently reports when part of its investigation could not be completed.
**Given:** The system's investigation plan has three steps for Site 003: (1) eCRF entry delay analysis, (2) data correction rate analysis, (3) CRA staffing change review. Step 2 fails with a "database connection timeout."
**When:** The system completes its investigation.
**Then:** The system's final review includes the results of all three steps — the successful entry delay analysis, the failed correction analysis (with the error message "database connection timeout"), and the successful CRA staffing review. The failure is visible, not silently ignored.

**UAT-3.3: All data sources fail simultaneously, but the system still returns a structured response**

**Scenario:** A Clinical Data Manager runs an analysis during a complete database outage.
**Given:** All five data quality data sources (eCRF entry delays, outstanding queries, data corrections, CRA staffing history, monitoring visits) are returning errors.
**When:** The user asks any data quality question.
**Then:** The system completes without crashing. All data sections are empty. The system reports a confidence of 0.5 (acknowledging limited data). It returns a structured response rather than an error page.

---

### UAT Group 4: The System Tailors Its Investigation to Match Its Initial Hypothesis (2 cases)

**UAT-4.1: Different hypotheses lead to different investigation steps**

**Scenario:** A Clinical Data Manager wants to verify the system is not running the same analyses regardless of the question asked.
**Given (Run A):** The system's initial analysis produces the hypothesis "Site 003 entry lag is critically high." Its investigation plan selects the eCRF entry delay analysis and data correction analysis for Site 003.
**When (Run A):** The user asks "Check entry lag."
**Then (Run A):** The system runs the eCRF entry delay analysis focused on Site 003.

**Given (Run B):** The system's initial analysis produces the hypothesis "CRA transition at Site 005 caused a quality dip." Its investigation plan selects the CRA staffing change history for Site 005.
**When (Run B):** The user asks "Check CRA issues."
**Then (Run B):** The system runs the CRA staffing change history focused on Site 005 — a different analysis than Run A, proving the investigation was tailored to the hypothesis.

**UAT-4.2: No hypotheses means no targeted investigation steps are run**

**Scenario:** A Clinical Operations Lead wants to confirm the system does not run unnecessary analyses when it finds no initial concerns.
**Given:** The system's initial analysis produces no hypotheses (i.e., no concerns were identified from the overview data).
**When:** The user asks any question.
**Then:** The system gathers its initial overview data but does not run any targeted follow-up analyses — confirming it only investigates when it has a reason to.

---

### UAT Group 5: The System Runs Multiple Specialist Investigations in Parallel (3 cases)

**UAT-5.1: A cross-domain question triggers investigations by both the Data Quality and Enrollment specialists**

**Scenario:** A Clinical Operations Director asks a broad question that spans data quality and enrollment.
**Given:** The system determines the question requires both the Data Quality specialist and the Enrollment specialist, and that a combined summary is needed.
**When:** The user asks "Full overview."
**Then:** The response includes findings from both specialists. Each specialist's investigation audit trail shows all five steps (Gather Data, Analyze, Plan, Investigate, Reflect). A cross-domain summary highlights findings that span both areas.

**UAT-5.2: If one specialist crashes, the other still returns its findings**

**Scenario:** A Clinical Operations Director asks a cross-domain question, but one specialist encounters an internal error.
**Given:** The system routes the question to both specialists. The Data Quality specialist crashes during its analysis phase. The Enrollment specialist completes normally and identifies a 45% screen failure rate at Site 003.
**When:** The user submits any cross-domain question.
**Then:** The response includes the Enrollment specialist's findings but not the Data Quality specialist's. The cross-domain summary section is empty (since only one specialist produced results), rather than showing an error.

**UAT-5.3: The live progress feed shows the full sequence: routing, both specialists' phases, and final synthesis**

**Scenario:** A user watches the live progress feed while a cross-domain investigation runs.
**Given:** The system routes the question to both specialists and requires a combined summary.
**When:** The user submits any cross-domain question.
**Then:** The live progress feed shows events in this order: (1) "Routing" from the coordinator, then (2) investigation phases (Gather Data, Analyze, Plan, Investigate, Reflect) from both specialists, then (3) "Synthesize" from the coordinator. Both specialists appear in the feed.

---

### UAT Group 6: The System Correlates Findings Across Different Clinical Domains (3 cases)

**UAT-6.1: The cross-domain summary includes specific findings from both specialists**

**Scenario:** A Clinical Operations Director wants to see how data quality issues and enrollment issues at the same site are connected.
**Given:** The Data Quality specialist found "Mean eCRF entry lag of 12.4 days exceeds threshold" at Site 003. The Enrollment specialist found "Screen failure rate 45% vs. study average 22%" at Site 003.
**When:** The user asks "Full overview."
**Then:** The cross-domain summary references Site 003 from both specialists. The Data Quality findings section mentions Site 003 and the 12.4-day delay. The Enrollment findings section mentions Site 003.

**UAT-6.2: The cross-domain summary identifies sites that appear in both specialists' findings as hotspots**

**Scenario:** A Clinical Operations Director needs to identify sites with problems across multiple areas.
**Given:** Both the Data Quality and Enrollment specialists flagged Site 003. The combined analysis produces the insight "Site 003 entry lag spike coincides with screen failure surge" (confidence 0.88) with a priority action "Trigger urgent site visit for Site 003."
**When:** The user asks "Site 003 issues."
**Then:** The cross-domain findings section contains at least one entry, and that entry specifically names Site 003 as a cross-domain hotspot.

**UAT-6.3: When one specialist crashes, the cross-domain summary is skipped and the surviving specialist's findings are used directly**

**Scenario:** A Clinical Operations Director asks a cross-domain question, but one specialist fails.
**Given:** Both specialists were selected, and a combined summary was requested. The Data Quality specialist crashes during analysis. The Enrollment specialist completes normally.
**When:** The user submits any cross-domain question.
**Then:** The response includes only the Enrollment specialist's findings. The cross-domain summary step is skipped entirely (not attempted with incomplete data). The cross-domain findings section is empty.

---

### UAT Group 7: The System Uses the Correct Analysis Templates for Each Specialist (3 cases)

**UAT-7.1: The Data Quality specialist uses exactly three analysis steps with the correct inputs**

**Scenario:** A QA analyst wants to verify the Data Quality specialist follows its defined analysis workflow.
**When:** The user asks "test query" directed to the Data Quality specialist.
**Then:** The system performs exactly three analysis steps: (1) Analyze — receiving the gathered data and the user's question, (2) Plan — receiving the hypotheses and available analyses, (3) Reflect — receiving the question, hypotheses, investigation results, and iteration count. No extra or missing steps.

**UAT-7.2: The Enrollment specialist uses its own analysis steps, not the Data Quality specialist's**

**Scenario:** A QA analyst wants to confirm each specialist has its own separate analysis workflow.
**When:** The user asks "enrollment test" directed to the Enrollment specialist.
**Then:** The system uses the Enrollment specialist's analysis steps (not the Data Quality specialist's). None of the Data Quality specialist's templates appear in the process.

**UAT-7.3: The routing step includes prior conversation context when available**

**Scenario:** A Clinical Operations Lead is in a multi-turn conversation and wants follow-up answers that reflect prior discussion.
**Given:** The prior conversation included a discussion about Site 007 enrollment delays.
**When:** The user asks a follow-up question "What about Site 007?"
**Then:** The routing step's analysis includes the prior conversation context "Prior exchange about Site 007 enrollment delays" — ensuring the follow-up is interpreted in context.

---

### UAT Group 8: The Investigation Audit Trail Is Complete and Ordered (2 cases)

**UAT-8.1: A single-pass investigation records all five steps with appropriate details**

**Scenario:** An auditor reviews the system's investigation trail for regulatory compliance.
**Given:** The system generates 2 hypotheses, plans 2 investigation steps, executes 2 analyses, and determines the investigation is complete.
**When:** The user asks any question that completes in one investigation pass.
**Then:** The investigation audit trail has exactly 5 entries in this order:
1. **Gather Data** — includes a summary of data collected
2. **Analyze** — notes 2 hypotheses were generated
3. **Plan** — notes 2 steps were planned
4. **Investigate** — notes 2 analyses were executed
5. **Reflect** — notes the investigation goal was satisfied

**UAT-8.2: A two-pass investigation records 10 steps, correctly grouped by pass**

**Scenario:** An auditor reviews a multi-pass investigation for completeness.
**Given:** The first pass determines the investigation is incomplete. The second pass determines it is complete.
**When:** The system completes a two-pass investigation.
**Then:** The investigation audit trail has exactly 10 entries. Entries 1–5 are labeled as Pass 1. Entries 6–10 are labeled as Pass 2. Within each pass, the phases appear in order: Gather Data, Analyze, Plan, Investigate, Reflect.

---

### UAT Group 9: The Analysis Output Accurately Reflects Findings (4 cases)

**UAT-9.1: A "Critical" severity finding is reported as Critical, not downgraded**

**Scenario:** A Clinical Operations Lead needs to trust that the system's severity ratings match the underlying analysis.
**Given:** The system's final review classifies the overall severity as "Critical" with the finding "Critical data breach" at Site 001 (confidence 0.99).
**When:** The user asks any data quality question.
**Then:** The output severity is displayed as "Critical" — not "Medium" or any other default.

**UAT-9.2: The summary names all affected sites**

**Scenario:** A Clinical Operations Lead reviews the summary to identify which sites need attention.
**Given:** The system's final review identifies findings at three sites: Site 001 (entry lag issue), Site 003 (high query burden), and Site 007 (CRA transition impact).
**When:** The user asks any data quality question.
**Then:** The output summary mentions Site 001, Site 003, and Site 007 — all three affected sites appear.

**UAT-9.3: When the Data Quality specialist finds no issues, a clear "no issues" message is shown**

**Scenario:** A Clinical Data Manager checks data quality and wants confirmation when everything looks normal.
**Given:** The Data Quality specialist's final review returns no findings and a Low severity.
**When:** The user asks any data quality question.
**Then:** The output summary reads "No significant data quality issues detected." The confidence is 0.5.

**UAT-9.4: When the Enrollment specialist finds no issues, a clear "no issues" message is shown**

**Scenario:** A Clinical Operations Lead checks enrollment status and wants confirmation when everything looks normal.
**Given:** The Enrollment specialist's final review returns no findings and a Low severity.
**When:** The user asks any enrollment question.
**Then:** The output summary reads "No significant enrollment issues detected." The confidence is 0.5.

---

### UAT Group 10: Data Quality Investigation — End-to-End (10 cases)

**UAT-10.1: A standard data quality investigation produces structured findings**

**Scenario:** A Clinical Data Manager asks a routine data quality question.
**When:** The user asks "Which sites have data quality issues?"
**Then:** The response identifies itself as a data quality analysis. The severity is High. Two findings are listed. The summary specifically mentions Site 003.

**UAT-10.2: A two-pass investigation upgrades findings when the second pass reveals more**

**Scenario:** A Clinical Data Manager asks for a deep investigation that requires two passes.
**Given:** The first investigation pass determines more analysis is needed. The second pass completes with a High severity rating.
**When:** The user asks "Deep investigation."
**Then:** The investigation audit trail shows two data-gathering steps and two review steps. The final severity is High (reflecting the second pass's conclusion).

**UAT-10.3: The initial data gathering queries all five data quality data sources**

**Scenario:** A QA analyst verifies the system collects comprehensive data before analyzing.
**When:** The user asks any data quality question.
**Then:** The system queries all five data quality sources in the initial data-gathering step: eCRF entry delays, outstanding queries, data corrections, CRA staffing history, and monitoring visits.

**UAT-10.4: Targeted investigation steps use the correct site filter**

**Scenario:** A Clinical Data Manager wants to verify the system investigates the correct site.
**Given:** The investigation plan specifies running an eCRF entry delay analysis for Site 003.
**When:** The user asks any question.
**Then:** The eCRF entry delay analysis is executed with Site 003 as the filter — not a different site or all sites.

**UAT-10.5: The live progress feed reports all five investigation phases**

**Scenario:** A user watches the progress feed during an investigation.
**When:** The user asks any data quality question with the live progress feed enabled.
**Then:** The progress feed reports all five phases: Gather Data, Analyze, Plan, Investigate, and Reflect.

**UAT-10.6: A lost network connection during investigation does not crash the system**

**Scenario:** A user's browser loses its WebSocket connection while the system is mid-investigation.
**Given:** The live progress feed connection drops (simulated as a connection error on every progress update).
**When:** The user submits any data quality question.
**Then:** The system completes the investigation successfully despite the lost connection. The findings are available when the user reconnects.

**UAT-10.7: A garbled AI response during analysis does not crash the system**

**Scenario:** The underlying AI model returns an unparseable response during the analysis phase.
**Given:** The AI model returns plain text instead of structured analysis output.
**When:** The user asks any question.
**Then:** The system recovers gracefully — it uses a default hypothesis and continues the investigation rather than crashing. A valid response is returned to the user.

**UAT-10.8: When the system finds nothing to investigate, no targeted analyses are run**

**Scenario:** A Clinical Data Manager asks a question, but the system's analysis finds no concerns to investigate further.
**Given:** The analysis phase produces an empty investigation plan (no steps).
**When:** The user asks any question.
**Then:** The system performs only the initial data gathering. No targeted follow-up analyses are executed.

**UAT-10.9: The investigation audit trail records all five phases in the correct order**

**Scenario:** An auditor reviews the investigation trail for a single-pass investigation.
**When:** The user asks any question that completes in one pass.
**Then:** The investigation audit trail lists five phases in this exact order: Gather Data, Analyze, Plan, Investigate, Reflect.

**UAT-10.10: The overall confidence score is the average of individual finding confidences**

**Scenario:** A Clinical Operations Lead wants to understand how the system calculates its overall confidence.
**Given:** The system produces two findings: one with 0.92 confidence and one with 0.78 confidence.
**When:** The user asks any question.
**Then:** The overall confidence score is 0.85 (the average of 0.92 and 0.78, within a tolerance of 0.01).

---

### UAT Group 11: Enrollment Investigation — End-to-End (3 cases)

**UAT-11.1: A standard enrollment investigation identifies a site with high screen failure**

**Scenario:** A Clinical Operations Lead asks about screen failure rates.
**When:** The user asks "Which sites have high screen failure?"
**Then:** The response identifies itself as an enrollment funnel analysis. The severity is High. One finding is listed. The summary specifically mentions Site 007.

**UAT-11.2: The initial data gathering queries all six enrollment data sources**

**Scenario:** A QA analyst verifies the system collects comprehensive enrollment data.
**When:** The user asks any enrollment question.
**Then:** The system queries all six enrollment sources in the initial data-gathering step: screening pipeline, enrollment rate, screen failure patterns, regional benchmarks, site enrollment summary, and investigational product kit inventory.

**UAT-11.3: When the Enrollment specialist finds no issues, a clear "no issues" message is shown**

**Scenario:** A Clinical Operations Lead checks enrollment and everything looks normal.
**Given:** The Enrollment specialist's final review returns no findings and a Low severity.
**When:** The user asks any enrollment question.
**Then:** The output summary reads "No significant enrollment issues detected." The confidence is 0.5.

---

### UAT Group 12: Questions Reach the Right Specialist (3 cases)

**UAT-12.1: A data quality question is routed to the Data Quality specialist only**

**Scenario:** A Clinical Data Manager asks a question specifically about data quality.
**When:** The user asks "How is data quality?"
**Then:** The system routes the question to the Data Quality specialist only. No cross-domain summary is generated.

**UAT-12.2: A cross-domain question is routed to both specialists**

**Scenario:** A Clinical Operations Director asks a broad question spanning both domains.
**When:** The user asks "Overview of data quality and enrollment."
**Then:** The system routes the question to both the Data Quality specialist and the Enrollment specialist. A cross-domain summary is planned.

**UAT-12.3: A garbled routing response defaults to the Data Quality specialist**

**Scenario:** The system's internal routing logic encounters an unparseable AI response.
**Given:** The AI model returns garbled text instead of a valid routing decision.
**When:** The user asks any question.
**Then:** The system defaults to routing to the Data Quality specialist. The routing explanation indicates a parse error occurred.

---

### UAT Group 13: Full Analysis Pipeline Execution (7 cases)

**UAT-13.1: A single-specialist question skips the cross-domain summary**

**Scenario:** A Clinical Data Manager asks a question that only requires the Data Quality specialist.
**Given:** The system routes the question to the Data Quality specialist only, with no cross-domain summary needed.
**When:** The user asks a data quality question.
**Then:** The response contains findings from the Data Quality specialist. The cross-domain findings section is empty (no synthesis was performed).

**UAT-13.2: A multi-specialist question produces a cross-domain summary**

**Scenario:** A Clinical Operations Director asks a question that requires both specialists.
**Given:** The system routes the question to both specialists and determines a cross-domain summary is needed. The combined analysis finds "Site 003 entry lag spike coincides with enrollment slowdown."
**When:** The user asks "Full overview."
**Then:** The response contains findings from both specialists. The cross-domain findings section has at least one entry.

**UAT-13.3: A garbled cross-domain summary response returns a structured error instead of crashing**

**Scenario:** The AI model returns an unparseable response during the cross-domain synthesis step.
**Given:** Both specialists complete successfully, but the synthesis AI response is garbled.
**When:** The user asks any cross-domain question.
**Then:** The cross-domain summary reads "Synthesis could not be completed." An error indicator is present. The system does not crash.

**UAT-13.4: An unrecognized specialist in the routing decision is silently skipped**

**Scenario:** The routing logic references a specialist that does not exist in the system.
**Given:** The routing decision includes the Data Quality specialist and a nonexistent specialist.
**When:** The user asks any question.
**Then:** The response contains findings from the Data Quality specialist only. The nonexistent specialist is ignored without an error.

**UAT-13.5: The live progress feed includes a "Routing" event from the coordinator**

**Scenario:** A user monitors the live progress feed during an investigation.
**When:** The user asks any question with the live progress feed enabled.
**Then:** The progress feed includes a "Routing" event from the coordinator, confirming the question was analyzed for routing.

**UAT-13.6: The response contains all required sections**

**Scenario:** A QA analyst verifies the response structure is complete.
**When:** The user asks any question.
**Then:** The response includes: a unique query identifier, the original question, the routing decision, findings from each specialist, and the cross-domain summary section.

**UAT-13.7: Each specialist's findings include a complete investigation audit trail**

**Scenario:** An auditor verifies every specialist provides a traceable investigation record.
**When:** The user asks any question.
**Then:** Every specialist's output includes an investigation audit trail (a list of investigation steps taken).

---

## Part 2: Supporting System UAT Cases (64 tests)

---

### UAT Group 14: Analysis Tool Registration and Availability (8 cases)

| ID | Scenario | Expected Outcome |
|----|----------|------------------|
| 14.1 | Look up an analysis by name (e.g., "echo") and a nonexistent analysis | The known analysis is found; the nonexistent one returns nothing |
| 14.2 | List all registered analyses | Two analyses are listed with their correct names |
| 14.3 | View the text description of a registered analysis | The description includes the analysis name and what it returns |
| 14.4 | Run an analysis with a site filter (e.g., Site 001) | The analysis succeeds and returns data for the specified site |
| 14.5 | Attempt to run a nonexistent analysis | The system reports "not found" |
| 14.6 | Run an analysis that encounters a runtime error | The system reports the error message without crashing |
| 14.7 | Verify all 12 production analyses are registered | All present: eCRF entry delays, outstanding queries, data corrections, CRA staffing history, monitoring visits, site enrollment summary, screening pipeline, enrollment rate, screen failure patterns, regional benchmarks, IP kit inventory, and KRI snapshot |
| 14.8 | Check that every registered analysis has documentation | Every analysis has a non-empty name and a description longer than 10 characters |

---

### UAT Group 15: AI Response Parsing (15 cases)

| ID | Input | Expected Outcome |
|----|-------|------------------|
| 15.1 | A clean structured response | Parsed correctly into a data structure |
| 15.2 | A list response | Parsed correctly as a list |
| 15.3 | A response wrapped in a code block with a language tag | The content inside the code block is extracted and parsed correctly |
| 15.4 | A response wrapped in a code block without a language tag | Still extracted and parsed correctly |
| 15.5 | A response with explanatory text before the structured data | The structured data is found and parsed; the preamble is ignored |
| 15.6 | A response with commentary after the structured data | The structured data is found and parsed; the postscript is ignored |
| 15.7 | A response containing special characters within string values | Parsed correctly without confusing the parser |
| 15.8 | A completely unstructured text response with no data | The system raises a parse error (does not silently return garbage) |
| 15.9 | A response padded with extra whitespace | Whitespace is trimmed; data is parsed correctly |
| 15.10 | A realistic multi-finding review response in a code block | All fields parsed: goal satisfaction status, both findings extracted |
| 15.11 | Round-trip a data structure through the safe serializer | The output deserializes back to the original data |
| 15.12 | Serialize a very large list (1,000 items) with a size limit | The list is truncated with a note indicating the original count was 1,000 |
| 15.13 | Serialize a structure with one small field and one large list | The small field is preserved intact; the large list is truncated to fit the size limit |
| 15.14 | Serialize empty structures (empty list, empty object) | Returns the correct empty representations |
| 15.15 | Serialize a structure containing a date value | The date is correctly formatted as a string (e.g., "2025-01-15") |

---

### UAT Group 16: Conversation Context and Follow-Up Questions (6 cases)

| ID | Scenario | Expected Outcome |
|----|----------|------------------|
| 16.1 | Request conversation context for a session with no prior interactions | Returns an empty context (no prior conversation to reference) |
| 16.2 | Request context for a session with 3 prior question-and-answer exchanges | The context includes all three questions and their answers |
| 16.3 | A prior response is very long (1,000 characters) | The response is truncated to a reasonable length (500 characters) in the context |
| 16.4 | The user asks a follow-up like "Tell me more about Site 003" after a prior data quality discussion | The system recognizes this as a follow-up, enriches the question with prior context about Site 003, and routes it to the Data Quality specialist |
| 16.5 | The AI model returns garbled text when analyzing the follow-up | The system treats it as a new topic, preserves the original question text, and routes to both specialists as a safe default |
| 16.6 | The user asks "Tell me more" after a previous question | The follow-up analysis receives both the original question and the follow-up question for context |

---

### UAT Group 17: Alert Lifecycle and Suppression Rules (9 cases)

| ID | Scenario | Expected Outcome |
|----|----------|------------------|
| 17.1 | A High Entry Lag finding at Site 003 (confidence 0.92, Warning severity) generates an alert | One alert is created: status is Open, not suppressed, linked to the Data Quality specialist, severity is Warning, site is Site 003, title is under 300 characters |
| 17.2 | Attempt to create alerts from a nonexistent finding | No alerts are created (returns an empty list) |
| 17.3 | An active suppression rule exists for the Data Quality specialist | The alert is created with status Suppressed, and the suppression rule is linked |
| 17.4 | A suppression rule exists but expired yesterday | The alert is created as Open (the expired rule is ignored) |
| 17.5 | A suppression rule exists but is marked inactive | The alert is created as Open (the inactive rule is ignored) |
| 17.6 | A suppression rule exists for the Data Quality specialist but targets Site 999, not Site 003 | The alert for Site 003 is created as Open (the rule does not match this site) |
| 17.7 | A suppression rule matches both the specialist and the specific site (Site 003) | The alert is created as Suppressed |
| 17.8 | A suppression rule matches the specialist but targets a different finding type | The alert is created as Open (the rule does not match this finding type) |
| 17.9 | A global suppression rule exists (no specific specialist filter) | The alert is created as Suppressed (the wildcard rule matches any specialist) |

---

### UAT Group 18: Web Interface and API Endpoints (26 cases)

**Specialist Endpoints**

| ID | User Action | Expected Outcome |
|----|-------------|------------------|
| 18.1 | View the list of available specialists | The page loads successfully (HTTP 200) and returns a list |
| 18.2 | View specialist details | Each specialist entry shows an identifier, name, and description |
| 18.3 | Attempt to invoke a nonexistent specialist | The system returns "Not Found" (HTTP 404) with a "not found" message |
| 18.4 | View recent findings for the Data Quality specialist (limit 5) | The page loads successfully and returns a list of findings |

**Alert Management Endpoints**

| ID | User Action | Expected Outcome |
|----|-------------|------------------|
| 18.5 | View the alerts list | The page loads successfully; the response includes an alerts list and a total count |
| 18.6 | View a specific alert by its identifier | The alert details load successfully; the identifier matches the requested one |
| 18.7 | View a nonexistent alert (ID 999999) | The system returns "Not Found" (HTTP 404) |
| 18.8 | Suppress an alert with a reason and the suppressor's name | The alert status changes to Suppressed |
| 18.9 | Attempt to suppress a nonexistent alert | The system returns "Not Found" (HTTP 404) |
| 18.10 | Acknowledge an alert with the acknowledger's email | The alert status changes to Acknowledged |
| 18.11 | Attempt to acknowledge a nonexistent alert | The system returns "Not Found" (HTTP 404) |

**Question Submission Endpoints**

| ID | User Action | Expected Outcome |
|----|-------------|------------------|
| 18.12 | Submit a question: "Which sites are behind?" | The system accepts the question (HTTP 202) and returns a status of "accepted" with a unique query identifier |
| 18.13 | Submit an empty question | The system rejects it (HTTP 422 — validation error) |
| 18.14 | Check the status of a nonexistent query | The system returns "Not Found" (HTTP 404) |
| 18.15 | Submit a follow-up to a nonexistent query | The system returns "Not Found" (HTTP 404) |

**Dashboard Endpoints**

| ID | User Action | Expected Outcome |
|----|-------------|------------------|
| 18.16 | Open the Data Quality dashboard | The page loads successfully (HTTP 200) |
| 18.17 | View Data Quality dashboard details | The dashboard shows a list of sites (each with site identifier, total queries, and open queries) and a study-wide total query count |
| 18.18 | Open the Enrollment Funnel dashboard | The page loads successfully (HTTP 200) |
| 18.19 | View Enrollment Funnel dashboard details | The dashboard shows a list of sites (each with site identifier, randomized count, and percentage of target), plus the study-wide target and percentage of target |

**Data Feed Health Endpoints**

| ID | User Action | Expected Outcome |
|----|-------------|------------------|
| 18.20 | Check the data feed health status | The page loads successfully (HTTP 200) |
| 18.21 | View the overall health status | The status is either "healthy" or "degraded" |
| 18.22 | View individual data source health | Each data source shows its row count and the date of its latest data |
| 18.23 | Verify all data sources have non-negative row counts | Every data source's row count is zero or greater |

**Live Progress (WebSocket) Endpoints**

| ID | User Action | Expected Outcome |
|----|-------------|------------------|
| 18.24 | Connect to the live progress feed for a nonexistent query | The system sends an error message containing "not found" |
| 18.25 | Connect to the live progress feed for a completed query with cached results | The system immediately sends the cached result with a "complete" status |
| 18.26 | Connect to the live progress feed for a query that is currently being processed | The system sends an informational message indicating the query is "already being processed" |
