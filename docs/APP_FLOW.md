# Drishti — Application Flow

## 1. Primary User Journey

```text
LOGIN
  ↓
COMMAND CENTER
  ↓
INVESTIGATION QUEUE
  ↓
PROJECT INTELLIGENCE
  ↓
EVIDENCE REVIEW
  ↓
CREATE CASE
  ↓
VERIFY / REVIEW
  ↓
CASE UPDATE
  ↓
GENERATE REPORT
  ↓
OFFICER FEEDBACK
```

## 2. Command Center

Purpose: answer **"Where should I look first?"**

The first screen should contain:
- total works
- total value
- high-priority cases
- critical cases
- delayed works
- duplicate candidates
- compliance exceptions
- risk distribution
- district/state distribution
- investigation queue preview

Avoid turning every metric into a giant card. Use a restrained operational layout with one primary summary strip and information-dense analytical sections.

## 3. Investigation Queue

Default columns:
- priority
- work ID
- project
- district
- category
- primary signals
- latest status
- assigned officer
- last updated

Actions:
- open project
- create case
- filter
- sort
- export

Filters:
- geography
- category
- priority
- signal type
- case status
- data-quality status

## 4. Project Intelligence

Page structure:

```text
PROJECT HEADER
Project name / ID / location / status

WHY THIS PROJECT IS HERE
Concise investigation-priority explanation

SIGNALS
Cost | Progress Gap | Delay | Duplicate | ML

EVIDENCE
Observed value → benchmark/reference → deviation

PEER CONTEXT
Comparable projects and distributions

RELATED WORKS
Potentially related or duplicate candidates

TIMELINE
Sanction → start → progress → expected completion

VERIFY
Recommended verification checklist

CASE
Create / open existing investigation
```

## 5. Evidence Interaction

Clicking a signal should reveal:
- rule/model name
- observed value
- reference value
- calculation
- peer definition
- source data fields
- timestamp/version

Do not hide the reasoning behind a generic "AI detected anomaly" message.

## 6. Investigation Case Flow

```text
CREATE CASE
  ↓
OPEN
  ↓
ASSIGN
  ↓
UNDER REVIEW
  ↓
FIELD VERIFICATION
  ↓
┌────────────────────┬────────────────────┬────────────────┐
│ SUBSTANTIATED      │ NOT SUBSTANTIATED  │ ESCALATED      │
│ → RESOLVED         │ → CLOSED           │ (with record)  │
└────────────────────┴────────────────────┴────────────────┘
```

Case actions:
- add note
- attach evidence
- mark signal as reviewed
- request verification
- change status
- assign/reassign
- record feedback
- generate report

Closing as **not substantiated** (CLOSED) requires an outcome
classification (NOT_SUBSTANTIATED), a structured reason category
(documentation provided · legitimate delay · data-quality issue · false
duplicate candidate · approved variation · contextual exception · other)
and a short free-text explanation — all recorded in the case audit trail.
The original AI-generated signals remain untouched. AI-generated risk
flags require human verification and do not constitute findings of fraud.

## 7. Recommended Verification

For each signal, show an actionable verification item.

Examples:
- financial/physical mismatch → verify physical execution and payment milestones
- cost anomaly → compare estimate, work order and peer works
- duplicate candidate → verify asset location and related work records
- delay → verify current site status and extension documentation

## 8. Report Flow

```text
CASE
 ↓
REPORT PREVIEW
 ↓
SELECT INCLUDED EVIDENCE
 ↓
GENERATE
 ↓
PDF
```

The report should preserve the distinction between:
- detected signal
- supporting evidence
- officer observation
- official decision

## 9. Feedback Flow

After investigation:
```text
CONFIRMED CONCERN
FALSE POSITIVE
NEEDS VERIFICATION
```

Feedback becomes metadata for future evaluation of rules and models.

## 10. Error / Empty / Loading States

### Loading
Use skeleton rows and restrained progress indicators.

### Empty queue
Explain that no projects currently match the selected filters.

### Data-quality issue
Show the affected field and correction requirement rather than a generic error.

### Detection failure
Show job status and retry action.

### No peer group
Display "Insufficient comparable projects" rather than fabricating a benchmark.

## 11. Demo Flow

For the SIH demo:

1. Open Command Center.
2. Show high-priority queue.
3. Open one project.
4. Show four independent signals.
5. Expand evidence.
6. Show peer benchmark.
7. Show recommended verification.
8. Create investigation case.
9. Add an officer remark.
10. Generate audit report.
11. Show feedback classification.

This tells the complete product story in a short, coherent path.
