# Drishti — Agent Rules

## 1. Mission

Build Drishti as a credible investigation-support platform for MPLADS monitoring.

The product is not a generic AI dashboard and not a fraud-verdict engine.

## 2. Non-Negotiable Product Rules

### Rule 1 — Never call an anomaly fraud
Use:
- anomaly
- irregularity signal
- investigation indicator
- duplicate candidate
- potential concern

Do not use:
- fraud detected
- corrupt project
- guilty
- fraudulent contractor

unless explicitly quoting source material as a documented claim.

### Rule 2 — Preserve evidence
Every major alert must expose:
- what triggered it
- observed value
- reference/benchmark
- difference
- source rule/model
- recommended verification

### Rule 3 — No black-box risk number
A priority can be calculated internally, but the UI must explain the contributing signals.

### Rule 4 — Human remains in the loop
The system flags and explains. Officials review, verify, classify and decide.

### Rule 5 — Never fabricate data
If data is unavailable:
- show unavailable
- show insufficient evidence
- show insufficient peer group

Never invent a benchmark or source.

### Rule 6 — Label synthetic data
Any controlled demo/synthetic data must be visibly labelled as such.

### Rule 7 — Preserve provenance
Detection results should be tied to dataset, ruleset/model version and execution time.

## 3. Engineering Rules

### Backend
- Keep route handlers thin.
- Put business logic in services.
- Use Pydantic schemas for API boundaries.
- Use SQLAlchemy for persistence.
- Keep detection modules independently testable.
- Never perform expensive ML/NLP work directly inside a synchronous request if it can be a background job.

### Frontend
- Use TypeScript strictly.
- Keep API calls in service modules.
- Avoid duplicating business logic in components.
- Prefer reusable evidence/signal components.
- Use semantic HTML and accessible controls.

### Database
- Never store derived analytics as if they were source facts.
- Preserve dataset provenance.
- Version detection outputs.
- Record case transitions.

### Git Workflow
- Before making changes or performing other Git operations, check the working tree and pull the latest changes from the relevant base branch.
- Never discard or overwrite existing user changes to make a pull succeed. Stop and resolve or ask for guidance if local changes or conflicts prevent a safe pull.
- Create a new feature branch from the up-to-date base branch for every feature, fix or other requested change.
- Commit and push after every meaningful implementation stage so progress is preserved remotely. Commits must contain only the changes for that stage and must not include secrets or unrelated user work.
- After the feature is complete and validated, open a pull request from the feature branch and merge it through the pull request. Do not merge feature work directly into the base branch.

## 4. UI Rules

### Never build
- gradient hero sections
- purple/blue AI dashboard aesthetic
- excessive glassmorphism
- a grid of identical cards
- centered text everywhere
- decorative AI imagery
- giant circular risk gauges

### Build
- evidence ledgers
- dense operational tables
- restrained typography
- maps
- horizontal comparison bars
- timelines
- inline evidence expansion
- document-like report previews

### Typography
Do not use Inter.

Preferred:
- IBM Plex Sans / Serif
- Source Sans 3
- IBM Plex Mono

## 5. Component Rules

A component must have a reason to exist.

Before creating a card/container ask:
> Does this boundary improve information hierarchy?

If not, use whitespace, dividers or typography instead.

### Status
Never communicate status using color alone.

### Tables
Use tables for comparable records rather than converting everything into cards.

### Charts
Every chart must answer a specific operational question.

## 6. Detection Rules

### Cost anomaly
Always show peer definition.

Bad:
> Cost is high.

Good:
> ₹40L is above the P75 of comparable district/category projects.

### Progress mismatch
Show both values and the gap.

### Delay
Show expected vs elapsed duration.

### Duplicate candidate
Show similarity components rather than a single unexplained duplicate score.

### Isolation Forest
Describe the output as statistical unusualness.

## 7. Data Rules

Canonical distinction:

```text
SOURCE FACT
   ≠
DERIVED METRIC
   ≠
MODEL OUTPUT
   ≠
OFFICER CONCLUSION
```

The UI and schema should preserve these layers.

## 8. API Rules

Use versioned endpoints:

`/api/v1/...`

Return predictable structures.

Example:
```json
{
  "data": {},
  "meta": {
    "dataset_version": "demo-01",
    "generated_at": "..."
  }
}
```

Errors should be structured and user-safe.

## 9. Case Workflow Rules

Allowed lifecycle:

```text
OPEN
 ↓
UNDER_REVIEW
 ↓
FIELD_VERIFICATION
 ↓
RESOLVED / ESCALATED
```

Resolution classification:
- confirmed concern
- false positive
- needs verification

Every transition should create an audit event.

## 10. Report Rules

A report must distinguish:
- automated detection
- evidence
- peer context
- officer observations
- case status

Do not write automated conclusions as official findings.

## 11. Demo Rules

The demo must be deterministic.

Maintain at least one fixture that demonstrates:
- cost anomaly
- progress mismatch
- delay
- duplicate candidate
- ML anomaly

The main demo project should have enough evidence to demonstrate multi-signal convergence.

## 12. Coding Agent Workflow

Before implementing:
1. Read `PRD.md`.
2. Read `TRD.md`.
3. Read `ARCHITECTURE.md`.
4. Read `APP_FLOW.md`.
5. Read `DESIGN.md`.
6. Read `BACKEND_SCHEMA.md`.
7. Read `MEMORY.md`.
8. Follow this file.
9. Read `TASKS.md` and work only on the requested task.

After implementing:
1. Run tests.
2. Run lint/type checks where available.
3. Verify API contracts.
4. Verify empty/error/loading states.
5. Check the UI against `DESIGN.md`.
6. Do not add unrelated features.
7. Update task status only after verification.

## 13. Scope Control

For the 3-day MVP, prioritize:

```text
CORE DETECTION
>
EVIDENCE EXPLANATION
>
INVESTIGATION WORKFLOW
>
REPORTING
>
POLISH
>
EXTRAS
```

Do not spend core sprint time on future-scope features while mandatory workflow pieces are incomplete.

## 14. Future Features

Satellite, computer vision, document intelligence, graph analytics, predictive risk and LLM copilot are extension points.

Implement them only when the MVP workflow is stable.

## 15. Final Quality Gate

Before calling the product complete:

- [ ] Can a user identify which projects need attention?
- [ ] Can they understand why?
- [ ] Can they inspect the evidence?
- [ ] Can they compare with peers?
- [ ] Can they create an investigation case?
- [ ] Can they record verification?
- [ ] Can they generate an audit report?
- [ ] Can they provide feedback?
- [ ] Is synthetic data clearly labelled?
- [ ] Does the UI look like an investigation workstation rather than a generic AI dashboard?
