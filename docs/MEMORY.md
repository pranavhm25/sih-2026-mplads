# Drishti — Project Memory

## Project Identity

- Product: **Drishti**
- SIH Problem Statement: **26102**
- Organization: **MoSPI**
- Division: **Data Informatics & Innovation Division (DIID)**
- Category: **Software**
- Theme: **Smart Automation**

## Product Definition

Drishti is an **MPLADS Risk Intelligence & Investigation Platform**.

One-line description:

> Drishti continuously analyzes MPLADS works, identifies unusual patterns, explains why they are unusual, prioritizes them for investigation, and helps authorities investigate and document them.

## Core Principle

Drishti must not automatically declare a project fraudulent.

The system identifies:
- potential irregularities
- unusual patterns
- projects that warrant investigation

Authorized officials make final decisions.

## Core Workflow

```text
INGEST
 ↓
CLEAN & VALIDATE
 ↓
DETECT
 ↓
CORRELATE
 ↓
PRIORITIZE
 ↓
INVESTIGATE
 ↓
DOCUMENT
 ↓
FEEDBACK
```

## Detection Signals

### Cost anomaly
Compare project cost with comparable projects.

### Financial/physical mismatch
Compare financial progress with physical progress.

### Delay
Compare expected duration with elapsed duration.

### Duplicate candidate
Use:
- text similarity
- location proximity
- cost similarity
- category match
- time overlap

### Agency/contractor concentration
Use where the underlying data supports it.

### ML anomaly
Use Isolation Forest as an unusual-pattern detector.

## Evidence Fusion

The platform combines independent signals:

```text
Rules
+
ML
+
NLP
+
Peer Context
↓
Evidence Fusion
↓
Investigation Priority
```

Do not reduce the product to a single unexplained risk score.

## Signature Differentiators

1. Investigation-first design.
2. Rule → Evidence → Action.
3. Multi-signal convergence.
4. Human-in-the-loop workflow.
5. Audit-ready case management.
6. Contextual peer intelligence.

## Core Screens

1. Command Center
2. Investigation Queue
3. Project Intelligence
4. Investigation Case
5. Reports
6. Data / Rules administration

## Must-Have MVP

- real/permitted MPLADS dataset
- data cleaning and validation
- cost anomaly
- financial/physical mismatch
- delay detection
- duplicate candidate detection
- Isolation Forest
- peer benchmarking
- explainable investigation priority
- evidence breakdown
- multi-signal convergence
- Command Center
- Investigation Queue
- Project Intelligence
- geographic visualization
- case creation
- recommended verification
- audit report

## Should-Have

- contractor/agency concentration
- Risk Replay
- officer feedback
- compliance dashboard
- CAG-informed rule library
- better role-based views

## Future Scope

- satellite verification
- computer vision
- document intelligence
- graph analytics
- predictive risk trajectories
- LLM Investigation Copilot

## Recommended Stack

Frontend:
- React
- TypeScript
- Tailwind CSS
- shadcn/ui
- Recharts
- Leaflet

Backend:
- FastAPI
- Python
- SQLAlchemy
- Pydantic

Data:
- PostgreSQL

ML:
- Pandas
- NumPy
- scikit-learn
- Isolation Forest
- optional LOF

NLP:
- TF-IDF
- cosine similarity
- optional Sentence Transformers

Reports:
- ReportLab

## UI Memory

The interface must **not** look like a generic AI/SaaS template.

Avoid:
- gradients
- excessive rounded cards
- centered dashboard layouts
- Inter
- decorative blobs
- neon colors
- excessive shadows

Target:
- evidence ledger
- government/engineering workpaper feel
- restrained colors
- strong tables
- maps
- typographic hierarchy
- compact operational layouts
- IBM Plex Sans/Serif + Source Sans 3 + IBM Plex Mono

## Demo Story

```text
MPLADS DATA
 ↓
DETECTION ENGINE
 ↓
RULES + ML + NLP
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

## Source-of-Truth Rule

This file records the stable product decisions for the project. If a later implementation decision conflicts with this memory, explicitly evaluate the trade-off before changing the core investigation-first concept.
