# UX Vision: Clinical Operations Intelligence System

> A conversational, investigation-first interface for clinical trial oversight — powered by Agentic AI with full reasoning transparency.

---

## Seven Design Principles

### 1. Conversation-First
The natural language interface is not a chatbot sidebar. It is the **primary interaction mode** woven into every surface. "Why?" is one click away from every data point. The Intelligence Bar is omnipresent — `Cmd+K` or `/` opens it from any view.

### 2. Progressive Revelation
**Executive 10-second pulse** → site ranking → site detail → investigation trace → raw evidence. Users zoom fluidly between altitudes, never locked to a fixed level. Each layer answers the natural next question.

### 3. Trust Through Transparency
Every AI finding shows:
- **What data it examined** (source badges with freshness)
- **What hypotheses it considered** (including rejected ones)
- **What evidence supports its conclusion** (clickable references)
- **Its confidence level** (proportional badge)

The PRPA trace is a **user-facing trust mechanism**, not debugging metadata.

### 4. Alerts = Pre-Investigated Findings
Alerts arrive with an investigation already completed. They say *"here is what happened, why, and what to do"* — not just *"metric X exceeded threshold Y."* Every alert includes root cause analysis, evidence, and recommended actions.

### 5. Cross-Domain Correlation as Visual Language
When a site has compound risk (data quality + enrollment + monitoring), the connections are **visually obvious** — curved connection lines between domain cards, correlation banners, and unified timeline markers — not hidden in separate tabs.

### 6. Operational Tempo Awareness
- **Study Manager:** 15-minute daily review — Mission Control + flagged sites
- **Executive:** 5-minute weekly pulse — situation summary + critical alerts
- **CRA in the field:** Instant mobile answers — site briefing before a visit

The interface adapts to each cadence through role-adaptive views and responsive layouts.

### 7. No Dead Ends
Every metric leads to an explanation. Every explanation leads to evidence. Every evidence leads to action. Every action leads to follow-up. The system never presents information without a path forward.

---

## Information Architecture

```
PERSISTENT LAYER (always visible)
┌─────────────────────────────────────────────────────────┐
│  THE INTELLIGENCE BAR                                    │
│  [Study Pulse]  [Investigation Prompt]  [Quick Actions]  │
└─────────────────────────────────────────────────────────┘

FIVE PRIMARY VIEWS
┌──────────────────────────────────────────┐
│  1. MISSION CONTROL (Study Overview)     │
│     └─ 2. SITE CONSTELLATION (Rankings)  │
│           └─ 3. SITE DOSSIER (Deep Dive) │
│                 └─ 4. INVESTIGATION      │
│                      THEATER (AI Trace)  │
│  5. ALERT COMMAND (Triage + Action)      │
└──────────────────────────────────────────┘
```

Navigation uses **contextual zoom** (not tabs): click any entity to drill deeper, pinch/scroll out to broaden. `Cmd+K` or `/` opens the conversational prompt from anywhere.

---

## View 1: The Intelligence Bar (Persistent)

The most important UI element — always visible at the top of every view. Minimal height (~56px) to maximize content area.

### Left — Study Pulse
- Study name in Inter Semi-Bold
- Enrollment micro-progress bar: `420/595 — 70.6%` (thin horizontal bar, navy fill)
- Critical alert count: red badge with count
- Data freshness indicator: small dot — green (`2h ago`) or amber (`Stale: EDC 18h old`)

### Center — Investigation Prompt
A refined search/command bar (inspired by Linear's `Cmd+K`).

**Placeholder text:** *"Ask about any site, metric, or operational question..."*

**Behavior:**
- **Autocomplete** as user types: site IDs with risk status pills, suggested queries (*"Which sites are behind on enrollment?"*), metric names
- On submit, expands downward into an **Investigation Panel** overlaying the current view (like Slack's thread panel)
- Panel can be **pinned** as a right-side panel (30% width) or **maximized** to full Investigation Theater view
- Session history accessible via dropdown arrow

### Right — Quick Actions
- Alert bell icon with unacknowledged count badge
- User avatar with role label (Study Manager, Executive, CRA)
- "New Investigation" button (navy outline, appears on hover as solid)

---

## View 2: Mission Control (Landing Page)

**Answers: "What needs my attention right now?"**

### Band 1: Situation Summary (top 20%)

A natural-language paragraph generated by the Conductor agent — not a chart:

> *"Study M14-359 is at 70.6% enrollment with 420/595 randomized across 149 active sites. **3 sites require immediate attention**: SITE-012 has 2.5x average query burden with rising trend, SITE-041 experienced drug kit stockout affecting 2 randomizations, and SITE-022 shows compound cascade from a September CRA transition. **7 sites** have amber warnings. Japanese region shows mild entry lag elevation across 4 sites — potentially regional IT factor."*

**Provenance indicators:**
- Small badge: `Conductor Synthesis · 92% confidence · Updated 2h ago`
- Site IDs are clickable hyperlinks → Site Dossier
- Bolded phrases expand on hover for one-sentence detail
- Expand icon reveals the full reasoning chain

**Below the paragraph — KPI Chips:**

| Chip | Example | States |
|------|---------|--------|
| Randomized / Target | 420 / 595 | green / amber / red |
| Mean Entry Lag | 3.2 days | green / amber / red |
| Open Queries | 1,847 | green / amber / red |
| Critical Alerts | 3 | green / amber / red |
| Sites On Track | 82% | green / amber / red |
| Data Freshness | All feeds < 4h | green / amber / red |

Each chip is clickable — filters the constellation below to relevant sites.

### Band 2: Site Constellation (middle 60%)

An air-traffic-control-style **scatter plot** — the signature visual of the system.

**Axes and encoding:**
- **X-axis:** Enrollment progress (% of target)
- **Y-axis:** Data quality health score (composite)
- **Dot size:** Active alert count (larger = more alerts)
- **Dot color:** Risk status — charcoal (healthy), amber (warning), red (critical), pulsing red (immediate action)
- **Dot label:** Site ID on hover; persistent labels for flagged sites

**What it reveals at a glance:**
- Bottom-left quadrant = compound risk (low enrollment + poor data quality)
- Top-left = enrollment-specific constraint
- Bottom-right = data quality intervention needed
- Clusters by country = regional patterns

**Interactions:**
- **Click dot** → navigates to Site Dossier
- **Lasso-select multiple** → "What do these sites have in common?" (auto-triggers investigation)
- **Toggle overlays:** country coloring, site type, PI experience level
- **Recently changed sites** pulse gently (CSS animation, subtle)
- **Hover** → micro-card tooltip: site ID, country, top 3 metrics, one-line AI finding

**Below the scatter** — a sortable **Site Table** for users who prefer tabular data:

| Site ID | Country | Enrollment % | Entry Lag | Open Queries | Alert Count | Risk Status |
|---------|---------|-------------|-----------|--------------|-------------|-------------|
| SITE-012 | USA | 80% | 2.1d | 47 | 3 | Critical |

Table rows are clickable → Site Dossier.

### Band 3: Activity Stream (bottom 20%)

Chronological feed of system activity:
- `2h ago` — Data Quality investigation of SITE-012 query spike — **[View]**
- `6h ago` — Critical alert — SITE-041 kit inventory at zero — **[Investigate]**
- `1d ago` — SITE-022 entry lag returning to baseline — **[View trend]**

Each entry shows the source agent icon and confidence badge. Clicking **[View]** opens the Investigation Theater for that investigation.

---

## View 3: Site Constellation (Extended)

The scatter plot expanded to full screen with analysis tools.

### Left Panel (30%) — Filters and Lenses

**Filters:** Country, site type, risk status, severity, CRA assignment.

**Lens Toggles** — change what the scatter visualizes:

| Lens | X-Axis | Y-Axis | Color |
|------|--------|--------|-------|
| **Compound Risk** (default) | Enrollment % | Data quality score | Risk status |
| **Enrollment** | Screening volume | Screen failure rate | Enrollment vs target |
| **Data Quality** | Entry lag | Query rate | Correction rate |
| **Monitoring** | Days since last visit | Outstanding actions | Visit compliance |

### Main Panel (70%) — Interactive Constellation

Larger canvas with zoom/pan controls. Hover shows a **site micro-card** (ID, country, top metrics, latest AI finding one-liner). Click opens a slide-in preview panel from the right. Double-click navigates to full Dossier.

**Region clustering:** Optional overlay draws faint convex hulls around country groups, making regional patterns immediately visible.

---

## View 4: Site Dossier (Single Site Deep Dive)

**Answers: "What is the full picture of this site?"**

### Left Column (25%): Site Identity

```
┌──────────────────────┐
│  SITE-022             │
│  Houston TX, USA      │
│                       │
│  Type: Academic       │
│  Experience: High     │
│  Activated: 2024-05-15│
│                       │
│  CRA: CRA-147         │
│    since Sep 2024     │
│  Previous: CRA-089    │
│    May–Sep 2024       │
│    ⚠ Transition       │
│                       │
│  Enrollment: 3/5 (60%)│
│                       │
│  ┌────────────────┐   │
│  │ Compound Risk  │   │
│  │ CRA Transition │   │
│  │ Cascade        │   │
│  └────────────────┘   │
│                       │
│  [Investigate]        │
│  [Compare to Peers]   │
│  [Alert History]      │
└──────────────────────┘
```

### Center Column (50%): AI Findings + Metrics

**Domain Cards** — one per specialist agent, visually connected when cross-domain correlation exists.

#### Data Quality Card

```
┌─ DATA QUALITY ──────────────────────────────────────────┐
│                                                          │
│  Entry lag spike during CRA transition, now recovering   │
│                                                          │
│  ╭──────────────────────────────────╮                    │
│  │  ▁▂▃▅█▇▅▃▂▂  Entry Lag (12 wk)  │                    │
│  ╰──────────────────────────────────╯                    │
│                                                          │
│  Mean Entry Lag    4.2d  (was 16.2d peak)               │
│  Open Queries      23                                    │
│  Query Rate        0.95  (avg: 0.73)                    │
│                                                          │
│  Source: EDC extract · Updated 2h ago                    │
│  Confidence: [████████░░] 92%                            │
│                                                          │
│  💬 "What caused the entry lag spike at SITE-022?"       │
└──────────────────────────────────────────────────────────┘
```

**Provenance on every metric:**
- Source badge (e.g., `EDC extract`, `CTMS`, `IRT`)
- Freshness timestamp
- Confidence badge (proportional fill)
- Expand arrow → full reasoning chain from the specialist agent

#### Enrollment Card

```
┌─ ENROLLMENT ────────────────────────────────────────────┐
│                                                          │
│  Enrollment decelerated during CRA transition            │
│                                                          │
│  Screened ██████████ 8                                   │
│  Passed   ██████     5                                   │
│  Randomized ████     3    Target: 5                      │
│                                                          │
│  Screening Rate   0.8/mo  (was 1.2)                     │
│  Failure Rate     25%                                    │
│  Target Gap       -2                                     │
│                                                          │
│  Source: CTMS + IRT · Updated 4h ago                     │
│  Confidence: [███████░░░] 85%                            │
│                                                          │
│  💬 "Why did enrollment slow at SITE-022?"               │
└──────────────────────────────────────────────────────────┘
```

#### Cross-Domain Correlation Banner

When the Conductor synthesis identified a causal connection between domains, a banner appears connecting the relevant cards with a curved line:

```
┌─ CROSS-DOMAIN FINDING ──────────────────────────────────┐
│                                                          │
│  Connected finding: Entry lag spike, query burden        │
│  increase, and enrollment deceleration all trace to the  │
│  CRA transition on September 15. The binding constraint  │
│  is operational burden from query backlog, not patient   │
│  availability.                                           │
│                                                          │
│  Recommended: CRA handover support and temporary data    │
│  entry assistance.                                       │
│                                                          │
│  Source: Conductor Synthesis                              │
│  Confidence: [████████░░] 92%                            │
│  Evidence: 4 data points across 3 domains                │
│  [Expand full reasoning chain]                           │
└──────────────────────────────────────────────────────────┘
```

This banner is the **"10x moment"** — replacing 30 minutes of cross-referencing Spotfire, CTMS, and RBQM dashboards with one synthesized insight.

#### KRI Timeline

Multi-line sparkline chart showing all KRIs over time with faint amber/red threshold bands and event markers (CRA transitions, monitoring visits, supply events). Hovering a marker shows the event detail.

### Right Column (25%): Actions + History

- **Active Alerts:** Current alerts with `Acknowledge` | `Suppress` | `Investigate` buttons
- **Investigation History:** Past AI investigations for this site (click to reopen in Investigation Theater)
- **Site Conversation:** Mini NL prompt pre-scoped to this site: *"Ask about SITE-022..."*
- **Action Log:** Audit trail of all actions taken (acknowledged alerts, investigations launched, notes added)

---

## View 5: Investigation Theater (AI Reasoning Trace)

The view that makes this system **genuinely different from any clinical dashboard**. When a user asks a question, they watch the AI think in real-time.

### Layout

Vertical scrolling narrative with a **PRPA timeline rail** on the left side. The rail shows phase progression with connected nodes — current phase pulses, completed phases show checkmarks.

### Phase Progression (streams via WebSocket)

#### The Question
Displayed prominently at the top in large Inter Semi-Bold:

> *"Why is SITE-012 showing a query spike?"*

Metadata below: Asked by [User], [timestamp], Routed to Data Quality Specialist

#### Phase 1: Routing
```
┌─ ROUTING ───────────────────────────────────────────────┐
│  ● Routing to Data Quality specialist                    │
│    This question is about query patterns.                │
│    Confidence in routing: 97%                            │
└──────────────────────────────────────────────────────────┘
```

#### Phase 2: Gather Data
Items appear one by one as tools execute (scanning animation, not a spinner):

```
┌─ GATHERING DATA ────────────────────────────────────────┐
│  ✓ Querying eCRF entry data.............. 847 records    │
│  ✓ Querying query history................ 312 queries    │
│  ✓ Checking CRA assignment history....... 2 assignments  │
│  ● Loading monitoring visit log.......... (streaming)    │
└──────────────────────────────────────────────────────────┘
```

#### Phase 3: Analyze (hypotheses stream in)

```
┌─ ANALYZING ─────────────────────────────────────────────┐
│                                                          │
│  Considering three hypotheses:                           │
│                                                          │
│  1. CRA training gap — query concentration on Lab        │
│     Results and AE pages suggests proficiency issue      │
│                                                          │
│  2. Monitoring spike — recent visit may have triggered   │
│     query burst                                          │
│                                                          │
│  3. Site complexity — academic high-volume site          │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

#### Phase 4: Plan

```
┌─ INVESTIGATION PLAN ────────────────────────────────────┐
│                                                          │
│  I will:                                                 │
│  (1) Check CRF page distribution of queries              │
│  (2) Cross-reference monitoring visit dates              │
│  (3) Compare with peer sites of similar profile          │
│  (4) Examine CRA assignment timeline                     │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

#### Phase 5: Investigate (results stream per step)

```
┌─ INVESTIGATING ─────────────────────────────────────────┐
│                                                          │
│  Step 1: CRF page distribution                           │
│  Lab Results 38%, Drug Accountability 22%, AE 18%        │
│  → Concentration confirmed                               │
│                                                          │
│  Step 2: Monitoring visit cross-reference                │
│  Last visit 42 days ago, no triggered queries            │
│  → Monitoring spike ruled out                            │
│                                                          │
│  Step 3: Peer comparison                                 │
│  2.5x average for similar Academic sites                 │
│  → Genuinely anomalous                                   │
│                                                          │
│  Step 4: CRA timeline                                    │
│  Single CRA since activation — no transition             │
│  → CRA change ruled out                                  │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

#### Phase 6: Reflect (final structured answer)

```
┌─ FINDING ───────────────────────────────────────────────┐
│                                                          │
│  Finding: Query spike driven by Lab Results and Drug     │
│  Accountability pages                                    │
│                                                          │
│  Root Cause: Data entry proficiency gap (not CRA         │
│  transition or monitoring-triggered)                     │
│                                                          │
│  Evidence:                                               │
│  • Lab Results page: 38% of queries (norm: 18%)          │
│  • Drug Accountability: 22% of queries (norm: 12%)       │
│  • Query rate 2.5x peer average for Academic sites       │
│  • No monitoring visit correlation                       │
│                                                          │
│  Confidence: [████████░░] 92%                            │
│  Data sources: EDC (847 records), CTMS (2 CRA records)   │
│                                                          │
│  Recommended Action: Targeted training on Lab Results    │
│  and Drug Accountability CRF completion. Expected        │
│  40-50% query reduction within 3-4 weeks.                │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

#### Follow-Up Chips

Appear below the finding as clickable pills:

`Show query trend over time` · `Other sites with similar patterns?` · `Impact on database readiness?` · `Generate site action report`

### Interactive Elements

- All data references are clickable (opens source data in a side panel)
- Each phase is collapsible (click the phase header to collapse/expand)
- Export button generates a formatted PDF/Word report
- Share button copies a link to this investigation (persisted in investigation history)

---

## View 6: Alert Command (Triage Workflow)

### Left Panel (40%) — Alert Queue

Prioritized by severity then recency. Each alert card shows:

```
┌─────────────────────────────────────────┐
│  🔴 CRITICAL                             │
│  Query rate anomaly at SITE-012          │
│  Data Quality Agent · 2h ago             │
│                                          │
│  SITE-012 (USA) · 3 related alerts       │
│                                          │
│  "2.5x average query burden with         │
│   concentration on Lab Results pages"     │
│                                          │
│  Status: Unacknowledged                  │
└─────────────────────────────────────────┘
```

Filters: severity, domain, site, status (unacknowledged / acknowledged / suppressed).

### Right Panel (60%) — Alert Detail

Full detail view with the **pre-completed AI investigation inline** — the system already investigated this alert before the user opened it.

Sections:
1. **Alert Summary** — what triggered it, when, severity
2. **AI Investigation** — embedded Investigation Theater (collapsed by default, expandable) showing the full PRPA reasoning trace
3. **Recommended Actions** — specific, actionable next steps
4. **Related Alerts** — same site or similar pattern across sites
5. **Action Buttons:** `Acknowledge` | `Suppress (with reason + expiry)` | `Investigate Further` | `Assign to CRA`

---

## Key Interaction Patterns

### The "Why?" Pattern
Every metric and finding has a one-click path to investigation:
- **Hover** → tooltip with one-sentence AI explanation + provenance
- **Click** → contextual Investigation Panel with pre-formulated question
- **Type** → freeform question via Intelligence Bar

### The "Compare" Pattern
- Peer benchmarks displayed alongside every metric on Site Dossier (faint line showing average)
- Multi-select 2–5 sites from constellation for side-by-side comparison view
- Regional grouping auto-composes comparison questions (*"How do Japanese sites compare to US sites on entry lag?"*)

### The "Watchlist" Pattern
- Pin sites to a personal watchlist (persistent sidebar, collapsible)
- Watchlist briefing on login: *"SITE-022 entry lag improved from 8.3 to 4.2 days since your last session"*
- Watchlist alerts highlighted with a star icon in Alert Command

### The "Time Travel" Pattern
- Sparklines on every metric (last 12 weeks minimum)
- *"Was this the same pattern last quarter?"* triggers historical investigation
- Event markers on timelines: CRA transitions, monitoring visits, supply events, protocol amendments

### Clarification Handling
When queries are ambiguous, the system asks before investigating:

> *"I can investigate problem sites in several dimensions:*
> - *Sites with critical alerts (3 sites)*
> - *Sites behind enrollment targets (12 sites)*
> - *Sites with data quality issues (7 sites)*
> - *All of the above (cross-domain synthesis)"*

Selection chips appear inline. The user picks one (or types a clarification) and the investigation proceeds.

---

## Visual Design Language

### Design Philosophy

Apple-inspired: sleek, modern, minimalistic. Greyscale-dominant palette. Premium controls, refined typography, generous whitespace. Think Apple Health meets Bloomberg Terminal. Reduction is the primary design tool — remove visual noise, let content breathe.

### Color System

| Role | Color | Hex | Usage |
|------|-------|-----|-------|
| **Background** | Off-white | `#F8F9FA` | Page background. Not stark white — clinical eyes spend hours here. |
| **Panel** | Warm gray | `#F1F3F5` | Card and panel backgrounds |
| **Surface** | Light gray | `#E9ECEF` | Borders, dividers, subtle backgrounds |
| **Text Primary** | Dark charcoal | `#212529` | Headlines, primary content. Never pure black. |
| **Text Secondary** | Medium gray | `#6C757D` | Labels, metadata, timestamps |
| **Accent** | Deep navy | `#1B3A6B` | Actions, selections, links. Trustworthy, authoritative. |
| **AI Accent** | Subtle violet | `#6C63FF` | Exclusively for AI-generated content borders and badges |
| **Critical** | Red | `#DC3545` | Critical alerts, risk indicators |
| **Warning** | Amber | `#F59E0B` | Warning states |
| **Healthy** | Green | `#198754` | On-track indicators |
| **Info** | Blue | `#0D6EFD` | Informational states |

**Key rule:** Semantic colors (red, amber, green) are used sparingly — only for status indicators and threshold bands. The overall aesthetic is greyscale with navy accent. AI-generated content is distinguished by a left violet border.

### Typography

| Element | Font | Weight | Size |
|---------|------|--------|------|
| **Headlines** | Inter | Semi-Bold (600) | 20–28px |
| **Subheadings** | Inter | Medium (500) | 16–18px |
| **Body** | Inter | Regular (400) | 14–15px |
| **Metrics/Data** | JetBrains Mono | Regular (400) | 14px |
| **Labels** | Inter | Medium (500) | 12px, uppercase, letter-spaced |
| **AI Narrative** | Inter | Regular (400) | 15px, 1.7 line-height |

AI narrative text uses a left border in violet (`#6C63FF`), slightly larger line-height (1.7) for comfortable reading, and a subtle warm-gray background (`#F8F9FA`).

### Iconography

Line icons throughout — Lucide or Phosphor style. Never filled icons. Stroke weight: 1.5px. Color: charcoal (`#212529`) default, navy (`#1B3A6B`) for interactive elements. Icons are functional, not decorative.

### Key Visual Components

#### Site Health Dot
Three dimensions encoded in a single component:
- **Fill color:** Risk status (charcoal / amber / red)
- **Pulse animation:** Recent change detected (subtle CSS pulse)
- **Ring thickness:** Alert count (thicker ring = more alerts)

#### Confidence Badge
Pill shape with proportional fill. Examples:
- `[████████░░] 92%` — nearly full, dark charcoal fill
- `[██████░░░░] 65%` — two-thirds, amber fill
- Text label inside for accessibility

#### Provenance Badge
Small inline badge on every AI-generated element:
```
[Data Quality Agent · EDC + CTMS · 92% · 2h ago]
```
Click expands to full reasoning chain.

#### Sparkline + Threshold Bands
Every metric includes a 12-week sparkline with faint amber/red threshold bands drawn behind the line. The current value is a dot at the end. Event markers (vertical dashed lines) annotate significant events.

#### PRPA Phase Indicator
Vertical timeline with connected circular nodes:
- Completed: checkmark, filled charcoal
- Current: pulsing navy dot
- Pending: hollow gray circle
- Nodes connected by a thin vertical line

#### Cross-Domain Connection Line
Curved SVG line connecting domain cards on Site Dossier when AI found a causal link. The line is labeled at its midpoint with a brief explanation in a small pill.

### Data Visualization Rules

1. **No pie charts.** Use bar charts (comparisons), sparklines (trends), scatter (ranking/correlation), funnels (enrollment pipeline).
2. **Enrollment funnel:** Horizontal flow — `Screened → Passed → Randomized` — with stage percentages and counts. Greyscale bars with navy fill for the active stage.
3. **KRI heatmap:** Sites (rows) x KRIs (columns). Cells colored green/amber/red for instant pattern scanning. Row sorting by composite risk score.
4. **All charts** use greyscale with accent colors only for semantic meaning. Grid lines are faint (`#E9ECEF`). Axis labels in Inter Medium 12px.

---

## Mobile: CRA Field Mode

CRAs need instant site-specific answers between monitoring visits. The mobile experience is purpose-built, not a responsive shrink of desktop.

### Home — My Sites
Only assigned sites, ranked by urgency. Compact cards:

```
┌─────────────────────────────────────┐
│  SITE-022 · Houston TX        🔴 3  │
│  Last visit: 14 days ago            │
│  "Entry lag improving, query        │
│   backlog still elevated"           │
└─────────────────────────────────────┘
```

### Site Quick View
Single-column dossier optimized for thumb-scrolling:
1. AI summary paragraph (with provenance)
2. Key metrics (4 tiles in 2x2 grid)
3. Active alerts (swipe to acknowledge)
4. "Ask about this site" prompt (bottom sheet)

No scatter plots on mobile — replaced by a ranked site list with risk indicators.

### Voice Query
Intelligence Bar supports voice input. *"What should I focus on at SITE-022?"* returns a spoken-style briefing optimized for audio consumption.

### Offline Mode
- Last AI summary, metrics snapshot, and alerts cached locally
- Offline indicator in the Intelligence Bar
- Queued actions sync on reconnect
- Cache refresh on app foreground

### Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| **Desktop** (1200px+) | Full multi-panel layouts (3-column Dossier, split-panel Alert Command) |
| **Tablet** (768–1199px) | Two-panel layouts, constellation table with sparklines |
| **Mobile** (<768px) | Single-column cards, Intelligence Bar as bottom sheet, Investigation Theater as full-screen scroll |

---

## What Makes This Visionary (Not Incremental)

| Today's Tools (Spotfire, JReview, CluePoints) | This System |
|-----------------------------------------------|-------------|
| Metric-first: show numbers, user interprets | **Investigation-first**: AI-reasoned findings, data as evidence |
| Siloed by domain: EDC, CTMS, RBQM are separate apps | **Cross-domain synthesis** visible on every surface |
| Static drill-down: click site → see metrics → dead end | **Conversational drill-down**: ask why, follow up, compare |
| Alert = "metric X > threshold Y" | **Alert = pre-investigated finding** with root cause and action |
| No reasoning shown | **Full PRPA trace** — watch the AI think in real-time |
| No memory between sessions | **Session continuity**: follow-ups remember prior context |
| Same view for everyone | **Role-adaptive**: exec summary vs. CRA field briefing |

### The "10x Moments"

**Study Manager:** Asks *"Why is SITE-022 behind on enrollment?"* — receives in 20 seconds a synthesized answer that would take 45 minutes of cross-referencing CTMS, EDC, and CRA spreadsheets.

**Clinical Ops Leader:** Opens Mission Control and reads one paragraph that tells them what needs attention today — replacing the Monday ritual of five dashboards and three email reports.

**CRA in the field:** Opens the app before a site visit and gets a targeted briefing: *"Focus on Lab Results and Drug Accountability CRF completion — these pages drive 60% of query burden. Entry lag improved since your last visit but still above average."*

---

## Backend Integration

### API Enhancements Needed

The existing API is well-designed. Four additions complete the frontend picture:

| Endpoint | Purpose | View |
|----------|---------|------|
| `GET /api/study/summary` | Aggregate KPIs for Mission Control (enrollment progress, alert counts, stale feeds) in one call | Mission Control |
| `GET /api/sites/{site_id}/dossier` | Bundled response: site metadata + latest findings per agent + active alerts + KRI history + CRA assignments | Site Dossier |
| WebSocket enrichment | Include tool invocation results and hypothesis text in streaming events (not just phase names) | Investigation Theater |
| `GET/PUT /api/user/preferences` | Watchlist, preferred view, notification settings, role | All views |

### Critical Backend Files for Frontend Integration

| File | What It Defines | Frontend View |
|------|-----------------|---------------|
| `backend/routers/ws.py` | WebSocket streaming protocol | Investigation Theater real-time |
| `backend/schemas/query.py` | `QueryStatus` (routing, agent_outputs, synthesis) | Response rendering across views |
| `backend/schemas/dashboard.py` | `SiteDataQualityMetrics`, `SiteEnrollmentMetrics` | Constellation + Dossier |
| `backend/agents/base.py` | `AgentContext`, `AgentOutput`, reasoning trace | Investigation Theater |
| `backend/schemas/alert.py` | `AlertDetail` | Alert Command view |

### Frontend Technology Recommendations

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| **Framework** | React + Next.js | SSR for initial load, CSR for interactions. PWA for mobile. |
| **Real-time** | WebSocket client | Connects to `/ws/query/{id}` for streaming PRPA phases |
| **Constellation** | D3.js | Custom interactivity (lasso, zoom, overlays) |
| **Standard Charts** | Recharts or Nivo | Sparklines, bar charts, funnels |
| **Styling** | Tailwind CSS | Custom design tokens for the greyscale palette |
| **Icons** | Lucide React | Line icons, 1.5px stroke, consistent style |
| **Typography** | Inter + JetBrains Mono | Via Google Fonts or self-hosted |
| **State** | Zustand or Jotai | Lightweight, minimal boilerplate |
| **Mobile** | PWA (same codebase) | Service worker for offline, push notifications |

---

## Verification Checklist

After implementation, verify:

- [ ] The Intelligence Bar is accessible from every view (never hidden, never obscured)
- [ ] A user can go from Mission Control → Site Dossier → Investigation Theater in 2 clicks
- [ ] The Investigation Theater streams PRPA phases in real-time (not loading spinners)
- [ ] Cross-domain findings display the correlation banner on Site Dossier
- [ ] Every metric has a one-click "Why?" path to investigation
- [ ] Every AI-generated element shows provenance (source, confidence, timestamp)
- [ ] Alerts show pre-investigated findings, not just threshold breaches
- [ ] Mobile CRA mode shows only assigned sites with offline capability
- [ ] No view is a dead end — every piece of information leads somewhere
- [ ] Greyscale palette is dominant; semantic colors used sparingly for status only
- [ ] Typography hierarchy is clear: Inter for text, JetBrains Mono for data
- [ ] Whitespace is generous — content breathes (Apple reduction principle)
