# SIH 2026 --- Problem Statement 26102

## MPLADS AI Risk Intelligence & Investigation Platform

**Working Product Name:** Drishti\
**PS ID:** 26102\
**Organization:** MoSPI\
**Department:** Data Informatics & Innovation Division (DIID)\
**Category:** Software\
**Theme:** Smart Automation

------------------------------------------------------------------------

# 1. The Problem --- Background & Current Situation

## What is MPLADS?

The Members of Parliament Local Area Development Scheme (MPLADS)
involves developmental works recommended by Members of Parliament and
implemented through district/state authorities and implementing
agencies.

A large amount of information can be associated with each work:

-   Work recommendation
-   Sanction
-   Estimated cost
-   Sanctioned amount
-   Expenditure
-   Payments
-   Physical progress
-   Financial progress
-   Completion status
-   Location
-   Sector/category
-   Implementing agency
-   Contractor/vendor information where available

## The Actual Problem

The problem is not simply a lack of data.

The problem is:

> **There is too much project and financial data for authorities to
> manually identify which works deserve attention first.**

Authorities need to identify things such as:

-   Projects with unusual expenditure patterns
-   Significant cost deviations
-   Financial progress substantially ahead of physical progress
-   Delayed or stalled projects
-   Potential duplicate works
-   Unusual concentration around an agency/contractor
-   Projects that differ significantly from comparable works
-   Data-quality and compliance issues
-   Projects that require field verification

## Current Situation

A simplified view of the existing workflow is:

``` text
MPLADS / e-SAKSHI Data
          ↓
       Dashboards
          ↓
    Human Monitoring
          ↓
   Manual Investigation
```

Our solution adds an intelligence layer:

``` text
MPLADS / e-SAKSHI Data
          ↓
   Intelligence Layer
          ↓
  Detect Irregularities
          ↓
 Explain the Evidence
          ↓
 Prioritize Investigation
          ↓
 Human Verification
          ↓
  Case / Audit Record
```

### Important Principle

The system should **not** automatically declare a project fraudulent.

It should identify:

> **Potential irregularities and projects that warrant investigation.**

AI detects unusual patterns; authorized officials make the final
decision.

------------------------------------------------------------------------

# 2. Core Solution

## Product

### Drishti --- MPLADS Risk Intelligence & Investigation Platform

### One-line description

> **Drishti continuously analyzes MPLADS works, identifies unusual
> patterns, explains why they are unusual, prioritizes them for
> investigation, and helps authorities investigate and document them.**

## Core Workflow

``` text
1. INGEST
      ↓
2. CLEAN & VALIDATE
      ↓
3. DETECT
      ↓
4. CORRELATE
      ↓
5. PRIORITIZE
      ↓
6. INVESTIGATE
      ↓
7. DOCUMENT
```

------------------------------------------------------------------------

# 3. Data Ingestion

The system ingests available MPLADS/e-SAKSHI data.

Typical fields:

``` text
Work ID
MP / Constituency
State
District
Location
Category
Description
Estimated Cost
Sanctioned Cost
Expenditure
Financial Progress
Physical Progress
Sanction Date
Start Date
Completion Date
Status
Implementing Agency
Contractor / Vendor information where available
Latitude / Longitude where available
```

The system should clearly distinguish:

-   Official data
-   Derived analytical fields
-   Controlled synthetic demonstration data

Synthetic data must never be presented as actual government records.

------------------------------------------------------------------------

# 4. Data Quality Engine

Before applying ML, validate and normalize the data.

Examples:

``` text
Completion Date < Sanction Date
        ↓
Data anomaly

Expenditure > Sanctioned Amount
        ↓
Financial anomaly

Physical Progress > 100%
        ↓
Data anomaly

Missing mandatory information
        ↓
Data-quality / compliance issue
```

This reduces false alerts caused by poor or inconsistent source data.

------------------------------------------------------------------------

# 5. Detection Engine

The detection engine combines multiple independent approaches.

## 5.1 Cost Anomaly

Compare the project against comparable projects.

Example:

``` text
Project Cost       ₹42 lakh
Peer Median        ₹25 lakh

Deviation          +68%
```

Potential signal:

> Cost significantly above comparable projects.

The system should provide the benchmark rather than simply saying the
amount is "high."

------------------------------------------------------------------------

## 5.2 Financial vs Physical Progress

Example:

``` text
Financial Progress      86%
Physical Progress       31%

Gap                     55 percentage points
```

Potential signal:

> Significant financial-physical progress mismatch.

This is an investigation indicator, not proof of wrongdoing.

------------------------------------------------------------------------

## 5.3 Delay Detection

Example:

``` text
Expected Duration       365 days
Elapsed                 530 days

Delay                   165 days
```

Potential signal:

> Delayed or potentially stalled work.

------------------------------------------------------------------------

## 5.4 Duplicate Work Detection

Potential duplicate candidates can be identified using multiple signals:

### Text similarity

``` text
"Construction of community hall at XYZ"
```

vs.

``` text
"Construction of community centre at XYZ"
```

### Location

``` text
Distance = 43 metres
```

### Cost

``` text
₹28 lakh vs ₹29 lakh
```

### Category

``` text
Community infrastructure
```

Potential duplicate score can combine:

``` text
Text Similarity
+
Location Proximity
+
Cost Similarity
+
Category Match
+
Time Overlap
```

------------------------------------------------------------------------

## 5.5 Contractor / Agency Concentration

Where data is available, analyze unusual concentration.

Example:

``` text
District Project Value      ₹12 Cr
Agency X                    ₹5.1 Cr

Agency Share               42.5%
```

This is not automatically evidence of wrongdoing.

It is a risk signal that may warrant contextual review.

------------------------------------------------------------------------

## 5.6 ML Anomaly Detection

Use unsupervised ML such as:

### Isolation Forest

Potential features:

``` text
Cost deviation
Expenditure ratio
Financial / physical gap
Delay
Project duration
Payment frequency
Peer percentile
Agency concentration
```

The ML model detects statistically unusual observations.

### Important distinction

Isolation Forest does **not** predict fraud.

It identifies unusual patterns.

The application combines:

``` text
ML anomaly
+
Rules
+
Peer context
+
NLP signals
```

to produce an investigation priority.

------------------------------------------------------------------------

# 6. Evidence Fusion

A central feature of Drishti is combining independent signals.

Example:

``` text
Cost anomaly                    🔴
Financial / physical mismatch   🔴
Delay                            🟠
Duplicate candidate              🔴
ML anomaly                       🟠
```

Instead of treating each alert independently:

``` text
Multiple independent signals
           ↓
      Evidence Fusion
           ↓
 Investigation Priority
```

The system can explain:

> **"Four independent indicators converge on this project."**

This is more useful than a black-box risk score.

------------------------------------------------------------------------

# 7. Explainable Risk / Investigation Priority

Do not display only:

``` text
Risk Score = 87
```

Instead display the underlying evidence.

Example:

## Project #MPL-10281

**Investigation Priority: HIGH**

### Signals

**1. Financial / Physical Mismatch**

``` text
Financial Progress: 84%
Physical Progress: 32%

Difference: 52 percentage points
```

**2. Cost Anomaly**

``` text
Project: ₹38.7L
Peer Median: ₹24.2L

Deviation: +60%
```

**3. Delay**

``` text
Expected: 365 days
Elapsed: 510 days

Delay: 145 days
```

**4. Duplicate Candidate**

``` text
Text Similarity: 91%
Location Distance: 43m
```

### Recommended Verification

``` text
□ Verify physical progress
□ Review payment records
□ Verify work order
□ Verify asset location
□ Compare related works
```

------------------------------------------------------------------------

# 8. Core Product Screens

## 8.1 Risk Command Center

The dashboard should answer:

> **Where should the authority look first?**

Example KPIs:

``` text
Total Works
Total Value
High-Priority Cases
Critical Cases
Delayed Works
Duplicate Candidates
Compliance Exceptions
```

Also include:

-   Risk distribution
-   State/district breakdown
-   Trend analysis
-   Geographic visualization
-   Top investigation cases

------------------------------------------------------------------------

# 9. Investigation Queue

Example:

  Priority   Work             District     Risk Main Signals        Action
  ---------- ---------------- ---------- ------ ------------------- -------------
  Critical   Community Hall   X              91 Cost + Progress     Investigate
  High       Road             Y              87 Duplicate + Delay   Investigate
  High       Water Tank       Z              74 Cost                Review

Instead of requiring officers to search thousands of projects, the
system produces a prioritized investigation queue.

------------------------------------------------------------------------

# 10. Investigation Workspace

When an officer opens a project:

``` text
PROJECT INTELLIGENCE

Project Details
       ↓
Risk Signals
       ↓
Evidence
       ↓
Peer Comparison
       ↓
Related Projects
       ↓
Timeline
       ↓
Recommended Actions
```

Actions:

``` text
[Create Investigation Case]

[Request Verification]

[Mark False Positive]

[Escalate]

[Generate Report]
```

This should be one of the main screens in the final demo.

------------------------------------------------------------------------

# 11. Investigation Case Management

Example:

``` text
CASE #INV-1028

Project:
Construction of Community Hall

Priority:
HIGH

Triggered Signals:
4

Status:
OPEN

Assigned Officer:
District Authority

Recommended Verification:
1. Physical verification
2. Payment verification
3. Work-order verification
4. Duplicate-project verification
```

Possible workflow:

``` text
OPEN
  ↓
UNDER REVIEW
  ↓
FIELD VERIFICATION
  ↓
RESOLVED / ESCALATED
```

------------------------------------------------------------------------

# 12. Audit Report Generator

One-click generation of an investigation report.

Report can contain:

``` text
Project Information

Risk Summary

Detected Anomalies

Supporting Evidence

Peer Comparison

Related Projects

Timeline

Recommended Verification

Officer Remarks

Investigation Status
```

Export formats:

-   PDF
-   CSV / structured export where appropriate

------------------------------------------------------------------------

# 13. Additional Features / Add-ons

These strengthen the solution but should not compromise the 3-day MVP.

## 13.1 Peer Benchmarking

Compare a project with:

-   Same district
-   Same sector
-   Same category
-   Same financial year
-   Similar project size

Example:

``` text
Project Cost       ₹40L
Peer Median        ₹24L
Peer P75           ₹31L

Project > Peer P75
```

------------------------------------------------------------------------

## 13.2 Risk Replay

Show how project risk changed over time.

``` text
January        Risk 20
    ↓
March          Risk 35
    ↓
May            Risk 57
    ↓
July           Risk 72
    ↓
September      Risk 89
```

This directly supports the early-warning aspect of the PS.

------------------------------------------------------------------------

## 13.3 CAG-Informed Rule Library

Use documented audit observations as inspiration for machine-detectable
patterns.

Concept:

``` text
Documented Audit Issue
        ↓
Machine-Detectable Pattern
        ↓
Rule
        ↓
Risk Signal
```

The rules should remain configurable and traceable to their
source/definition.

------------------------------------------------------------------------

## 13.4 Officer Feedback Loop

Officers can classify alerts:

``` text
Confirmed Concern
False Positive
Needs Verification
```

Store feedback for future analysis and model/rule improvement.

------------------------------------------------------------------------

## 13.5 Compliance Dashboard

Track categories such as:

``` text
Timeline Compliance
Financial Consistency
Data Completeness
Project Completion
Documentation Status
```

------------------------------------------------------------------------

# 14. Differentiation from Other SIH Solutions

Publicly available SIH26102 implementations already show convergence
around:

-   Isolation Forest
-   Rule-based anomaly detection
-   Cost anomaly detection
-   Duplicate detection
-   Risk scores
-   GIS
-   Contractor analysis
-   Dashboards
-   Explainable AI

Therefore, these should **not** be presented individually as our main
innovation.

## Our positioning

### Most basic approach

``` text
DATA
 ↓
ANALYTICS
 ↓
DASHBOARD
```

### Drishti

``` text
DATA
 ↓
DETECTION
 ↓
EVIDENCE
 ↓
PRIORITIZATION
 ↓
INVESTIGATION
 ↓
DOCUMENTATION
 ↓
FEEDBACK
```

------------------------------------------------------------------------

# 15. Differentiator 1 --- Investigation-First Design

Our central question is not:

> "What is anomalous?"

It is:

> **"What should an officer investigate, why, and what should they
> verify?"**

The dashboard is therefore only the entry point.

The main workflow is investigation.

------------------------------------------------------------------------

# 16. Differentiator 2 --- Rule → Evidence → Action

Every major alert should have three layers.

### Rule

Why does this condition matter?

### Evidence

What data caused the alert?

### Action

What should the officer verify?

Example:

``` text
RULE
Financial / physical mismatch

        ↓

EVIDENCE
84% financial
32% physical

        ↓

ACTION
Verify physical execution
and payment milestones
```

------------------------------------------------------------------------

# 17. Differentiator 3 --- Multi-Signal Convergence

Instead of relying on one anomaly:

``` text
Cost anomaly
     +
Delay
     +
Financial / physical mismatch
     +
Duplicate candidate
```

The system raises investigation priority when several independent
indicators converge.

------------------------------------------------------------------------

# 18. Differentiator 4 --- Human-in-the-Loop

The AI does not replace the authority.

``` text
AI
 ↓
Flag
 ↓
Explain
 ↓
Human Review
 ↓
Verification
 ↓
Decision
```

The system supports:

``` text
False Positive
Confirmed Concern
Needs Verification
```

This makes the platform more realistic for actual administrative use.

------------------------------------------------------------------------

# 19. Differentiator 5 --- Audit-Ready Workflow

Instead of ending at:

> "Risk = 87"

the system continues:

``` text
Risk
 ↓
Investigation
 ↓
Evidence
 ↓
Officer Remarks
 ↓
Case Status
 ↓
Audit Report
```

------------------------------------------------------------------------

# 20. Differentiator 6 --- Contextual Peer Intelligence

Instead of saying:

> "₹40 lakh is high."

the system says:

> "₹40 lakh is significantly above the comparable-project benchmark for
> the selected peer group."

The benchmark can be based on:

``` text
District
Category
Sector
Year
Project size
```

This provides context instead of relying only on global thresholds.

------------------------------------------------------------------------

# 21. Must-Have Features Before Final Submission

Given the 3-day runway, these should be treated as mandatory.

## 🔴 MUST HAVE

### Data

-   [ ] Real MPLADS dataset
-   [ ] Data cleaning
-   [ ] Data validation

### Detection

-   [ ] Cost anomaly
-   [ ] Financial vs physical mismatch
-   [ ] Delay detection
-   [ ] Duplicate candidate detection
-   [ ] Isolation Forest anomaly detection
-   [ ] Peer benchmarking

### Intelligence

-   [ ] Explainable investigation priority
-   [ ] Evidence breakdown
-   [ ] Multi-signal convergence

### Product

-   [ ] Command dashboard
-   [ ] Investigation queue
-   [ ] Project intelligence page
-   [ ] Geographic visualization
-   [ ] Investigation case creation
-   [ ] Recommended verification actions
-   [ ] Audit report generation

------------------------------------------------------------------------

# 22. Should-Have Features

If the core system is stable:

-   [ ] Contractor/agency concentration
-   [ ] Risk Replay
-   [ ] Officer feedback
-   [ ] Compliance dashboard
-   [ ] CAG-informed rule library
-   [ ] Better role-based views

------------------------------------------------------------------------

# 23. Future Scope

These should be presented as future expansion rather than attempted
during the 3-day sprint.

## 23.1 Satellite Verification

``` text
Project Location
       ↓
Satellite Imagery
       ↓
Construction Progress
       ↓
Cross-Validation
```

------------------------------------------------------------------------

## 23.2 Computer Vision

Analyze uploaded project photographs for:

-   Construction progress
-   Asset existence
-   Image duplication
-   Potentially manipulated images

------------------------------------------------------------------------

## 23.3 Document Intelligence

Use OCR/document AI on:

-   Sanction orders
-   Work orders
-   Invoices
-   Measurement books
-   Completion certificates

Then cross-check documents against structured data.

------------------------------------------------------------------------

## 23.4 Graph Analytics

Build relationship graphs:

``` text
MP
 │
District
 │
Agency
 │
Contractor
 │
Project
```

Then identify unusual relationship patterns.

------------------------------------------------------------------------

## 23.5 Predictive Risk

Move from:

> "This project is currently high risk."

towards:

> **"This project has an increasing risk trajectory and may require
> attention."**

------------------------------------------------------------------------

## 23.6 LLM Investigation Copilot

Future officer queries could include:

> "Why is this project high risk?"

> "Show similar projects."

> "What evidence should I verify?"

> "Summarize this case."

> "Generate an investigation report."

------------------------------------------------------------------------

# 24. Final Architecture

``` text
                    ┌──────────────────────┐
                    │ MPLADS / e-SAKSHI    │
                    │ Public Data          │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ DATA INGESTION       │
                    │ CSV / API / Dataset  │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ DATA QUALITY LAYER   │
                    │ Validation           │
                    │ Normalization        │
                    │ Deduplication        │
                    └──────────┬───────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
       ┌────────────┐   ┌─────────────┐  ┌────────────┐
       │ RULE       │   │ ML ENGINE   │  │ NLP ENGINE │
       │ ENGINE     │   │             │  │            │
       │            │   │ Isolation   │  │ Duplicate  │
       │ Compliance │   │ Forest      │  │ Detection  │
       │ Checks     │   │ LOF         │  │ Similarity │
       └─────┬──────┘   └──────┬──────┘  └─────┬──────┘
             │                 │               │
             └─────────────────┼───────────────┘
                               ▼
                    ┌──────────────────────┐
                    │ PEER BENCHMARKING    │
                    │ District / Category  │
                    │ Year / Sector        │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ EVIDENCE FUSION      │
                    │                      │
                    │ Multi-signal risk    │
                    │ Explainability       │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ RISK PRIORITIZATION  │
                    └──────────┬───────────┘
                               │
             ┌─────────────────┼─────────────────┐
             │                 │                 │
             ▼                 ▼                 ▼
      ┌────────────┐    ┌────────────┐   ┌─────────────┐
      │ COMMAND    │    │ INVESTIGA- │   │ ALERT       │
      │ CENTER     │    │ TION       │   │ ENGINE      │
      └────────────┘    │ WORKSPACE  │   └─────────────┘
                        └─────┬──────┘
                              │
                              ▼
                    ┌──────────────────────┐
                    │ CASE MANAGEMENT      │
                    │ Review               │
                    │ Verify               │
                    │ Escalate             │
                    │ Resolve              │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ AUDIT REPORT         │
                    │ PDF / Export         │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ OFFICER FEEDBACK     │
                    │                      │
                    │ False Positive       │
                    │ Confirmed Concern    │
                    │ Needs Verification   │
                    └──────────────────────┘
```

------------------------------------------------------------------------

# 25. Recommended Tech Stack

## Frontend

-   React
-   TypeScript
-   Tailwind CSS
-   shadcn/ui
-   Recharts
-   Leaflet

## Backend

-   FastAPI
-   Python
-   SQLAlchemy
-   Pydantic

## Database

-   PostgreSQL

SQLite can be used temporarily if deployment speed becomes a constraint.

## ML

-   Pandas
-   NumPy
-   Scikit-learn
-   Isolation Forest
-   Optional Local Outlier Factor

## NLP

-   TF-IDF
-   Cosine Similarity
-   Optional Sentence Transformers

## Reports

-   ReportLab

------------------------------------------------------------------------

# 26. Three-Day Implementation Priority

## DAY 1 --- Data + Intelligence

### Morning

-   Download/access dataset
-   Inspect structure
-   Clean data
-   Normalize fields
-   Create database

### Afternoon

Implement:

-   Data quality
-   Cost anomaly
-   Financial/physical mismatch
-   Delay detection
-   Peer benchmarking

### Evening

Implement:

-   Duplicate detection
-   Isolation Forest
-   Risk/evidence fusion
-   Explanations
-   Demo anomaly scenarios

------------------------------------------------------------------------

# DAY 2 --- Product

### Morning

Build:

-   Command Center
-   KPI cards
-   Risk distribution
-   Geographic visualization

### Afternoon

Build:

-   Investigation Queue
-   Project Intelligence page

### Evening

Build:

-   Investigation case management
-   Evidence view
-   Recommended actions

------------------------------------------------------------------------

# DAY 3 --- Differentiation + Submission

### Morning

Add:

-   Rule → Evidence → Action
-   Multi-signal convergence
-   CAG-informed rule references
-   Risk Replay if feasible

### Afternoon

Polish:

-   UI
-   Empty/error/loading states
-   Data labels
-   Demo scenarios
-   Deployment

### Evening

Prepare:

-   PPT
-   Architecture diagram
-   Demo flow
-   README
-   Screenshots
-   Final presentation narrative

------------------------------------------------------------------------

# 27. Final Product Story

The entire project can be summarized as:

``` text
                 MPLADS DATA
                      ↓
              DETECTION ENGINE
                      ↓
       ┌──────────────┼──────────────┐
       ↓              ↓              ↓
     RULES            ML             NLP
       └──────────────┼──────────────┘
                      ↓
               PEER CONTEXT
                      ↓
              EVIDENCE FUSION
                      ↓
             RISK PRIORITIZATION
                      ↓
             INVESTIGATION QUEUE
                      ↓
             INVESTIGATION CASE
                      ↓
              HUMAN VERIFICATION
                      ↓
                AUDIT REPORT
                      ↓
              OFFICER FEEDBACK
```

## Team Pitch

> **"MPLADS already generates large amounts of project and expenditure
> data, but authorities cannot manually inspect every work. Drishti adds
> an AI-powered risk intelligence layer that detects unusual cost,
> expenditure, progress, timeline and duplication patterns. More
> importantly, it explains why a project was flagged, compares it with
> similar projects, combines multiple independent signals, prioritizes
> cases for investigation, and provides a complete workflow from
> detection to investigation and audit reporting. We are not replacing
> the authority's decision --- we are helping the authority decide where
> to look first and what evidence to verify."**

## Core Differentiator

> ### **Detect → Explain → Prioritize → Investigate → Document**

**We are not building another fraud dashboard. We are building an
investigation workflow.**
