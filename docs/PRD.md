# Drishti — Product Requirements Document

**Problem Statement:** SIH 2026 — 26102  
**Working Product:** Drishti  
**Organization:** MoSPI  
**Division:** Data Informatics & Innovation Division (DIID)  
**Category:** Software  
**Theme:** Smart Automation

## 1. Product Summary

Drishti is an MPLADS risk-intelligence and investigation platform. It analyzes project, expenditure, progress, timeline, location, agency and related data to identify unusual patterns, explain the evidence behind them, prioritize projects for human investigation, and maintain an audit-ready case workflow.

Drishti does **not** declare a project fraudulent. It identifies potential irregularities and projects that warrant investigation. Authorized officials remain responsible for verification and decisions.

> **Core product story:** Detect → Explain → Prioritize → Investigate → Document → Learn

## 2. Problem

MPLADS generates substantial project and financial information, but manually inspecting every work is impractical. Authorities need a way to identify which works deserve attention first.

The product must surface signals such as:
- unusual expenditure patterns
- significant cost deviations
- financial progress substantially ahead of physical progress
- delayed or stalled projects
- potential duplicate works
- unusual agency/contractor concentration
- projects that differ materially from comparable works
- data-quality and compliance issues

The source brief explicitly frames the gap as an intelligence layer between data and human monitoring, rather than another dashboard. 

## 3. Goals

### Primary goals
1. Ingest and normalize MPLADS/e-SAKSHI-style project data.
2. Detect multiple classes of potential irregularity.
3. Provide contextual peer benchmarks.
4. Fuse independent signals into an explainable investigation priority.
5. Give officers a prioritized investigation queue.
6. Provide a project-level investigation workspace.
7. Create and manage investigation cases.
8. Generate audit-ready reports.
9. Capture officer feedback for future rule/model improvement.

### Non-goals for the 3-day MVP
- automatic fraud verdicts
- fully autonomous investigation decisions
- satellite verification
- advanced computer vision
- production-grade document AI
- predictive risk forecasting
- a general-purpose chatbot
- replacing official approval or verification processes

## 4. Users

### Primary user — Monitoring / Investigation Officer
Needs to:
- see where attention is required
- understand why a project was flagged
- inspect supporting evidence
- compare against similar projects
- record verification actions
- create and update cases
- generate reports

### Secondary user — Supervisory Authority
Needs to:
- monitor risk distribution
- review high-priority cases
- inspect district/state patterns
- review case status and escalation
- audit officer actions

### Data / System Administrator
Needs to:
- ingest datasets
- validate data
- manage rules
- inspect data-quality exceptions
- monitor model/rule execution

## 5. Product Principles

1. **Investigation-first:** the main outcome is a useful investigation workflow.
2. **Evidence before score:** every priority should be traceable to evidence.
3. **Context over arbitrary thresholds:** compare projects with meaningful peers.
4. **Human-in-the-loop:** AI flags; officials verify and decide.
5. **Independent signals:** combine rules, ML, NLP and peer context.
6. **Auditability:** preserve why an alert was produced and what happened afterward.
7. **Clear provenance:** distinguish official data, derived analytics and controlled synthetic demonstration data.

## 6. MVP Requirements

### R1 — Data ingestion
Support CSV/dataset ingestion for fields including:
- Work ID
- MP / constituency
- State
- District
- location
- category
- description
- estimated cost
- sanctioned cost
- expenditure
- financial progress
- physical progress
- dates
- status
- implementing agency
- contractor/vendor where available
- latitude/longitude where available

### R2 — Data quality
Detect:
- completion date earlier than sanction date
- expenditure above sanctioned amount
- physical progress above 100%
- missing mandatory fields
- duplicate records
- invalid or inconsistent values

### R3 — Cost anomaly
Compare project cost with a configurable peer group and expose:
- peer count
- median
- percentile
- project value
- deviation

### R4 — Financial/physical mismatch
Calculate and display the gap between financial and physical progress.

### R5 — Delay detection
Compare elapsed duration against expected duration and surface delayed/stalled candidates.

### R6 — Duplicate candidate detection
Use:
- text similarity
- location proximity
- cost similarity
- category match
- time overlap

The output must be a **duplicate candidate**, not a duplicate/fraud verdict.

### R7 — ML anomaly detection
Use Isolation Forest for unsupervised anomaly detection. ML output must be treated as an unusual-pattern signal, not a fraud prediction.

### R8 — Evidence fusion
Combine independent signals into an explainable investigation priority.

### R9 — Command Center
Show:
- total works
- total value
- high-priority cases
- critical cases
- delayed works
- duplicate candidates
- compliance exceptions
- risk distribution
- geographic distribution
- top investigation cases

### R10 — Investigation Queue
Provide sorting/filtering by priority, geography, signal type and status.

### R11 — Project Intelligence
Display:
- project details
- risk signals
- evidence
- peer comparison
- related projects
- timeline
- recommended verification actions

### R12 — Case management
Support:
- create case
- assign officer
- open
- under review
- field verification
- resolved (investigation concluded; classification recorded)
- escalated (substantiated concern raised to a higher authority)
- closed — not substantiated (human investigation did not substantiate
  the flagged concern; recorded with a structured reason + free-text
  explanation and a supervisor reopen path)
- false positive / confirmed concern / not substantiated / needs
  verification feedback

**AI FLAG ≠ FRAUD.** Drishti prioritizes investigations; it does not
determine guilt. A case closed as NOT_SUBSTANTIATED records that the
available evidence did not substantiate the flagged concern — it is not a
finding of fraud or of innocence, and it does not imply the automated flag
was wrong. Original AI-generated signals are immutable historical evidence
and are preserved on every cleared case and in every report.

### R13 — Audit report
Generate a structured report containing project information, risk summary, detected anomalies, evidence, peer comparison, related projects, timeline, recommended verification, remarks and status.

## 7. Should-Have Features

- contractor/agency concentration
- Risk Replay
- officer feedback loop
- compliance dashboard
- configurable CAG-informed rule library
- role-based views

## 8. Future Scope

- satellite-based progress cross-validation
- computer vision for construction photographs
- document intelligence/OCR for orders, invoices, measurement books and certificates
- relationship/graph analytics
- predictive risk trajectory
- LLM investigation copilot

## 9. Success Criteria

A successful demo should let a judge follow one continuous path:

**Dataset → anomaly → evidence → peer context → investigation priority → investigation case → verification checklist → audit report**

The platform should make the reason for every major alert understandable without requiring the user to trust a black-box score.

## 10. Demo Scenario

Use a controlled demonstration dataset with clearly labelled synthetic records if official records are unavailable.

Example case:
- financial progress: 84%
- physical progress: 32%
- project cost: ₹38.7L
- peer median: ₹24.2L
- elapsed: 510 days
- expected: 365 days
- duplicate text similarity: 91%
- location distance: 43m

The UI should show how these independent signals converge into an investigation priority, then allow the officer to create a case and generate a report.

## 11. MVP Priority

### Must have
Data ingestion, validation, cost anomaly, financial/physical mismatch, delay, duplicate candidates, Isolation Forest, peer benchmarking, evidence fusion, Command Center, Investigation Queue, Project Intelligence, geography, case creation, recommended actions and report generation.

### Should have
Agency concentration, Risk Replay, feedback, compliance dashboard, configurable rule references and enhanced role views.

## 12. Product Boundary

Drishti is a decision-support and investigation workflow system. It must never represent an analytical signal as proof of fraud, corruption or wrongdoing.
