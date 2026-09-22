# Drishti — Design System

## 1. Design Direction

### Product character

Drishti should look like a **serious government investigation workstation**, not a generic AI SaaS dashboard.

The visual language should communicate:
- evidence
- traceability
- geography
- public infrastructure
- operational urgency
- administrative credibility

### Explicitly avoid

- purple/blue AI gradients
- glassmorphism everywhere
- excessive rounded cards
- a card for every number
- centered text as the default
- giant hero headings
- decorative blobs
- excessive shadows
- generic "AI dashboard" illustrations
- Inter as the default typeface
- neon status colors
- every component looking like a floating container

## 2. Visual Concept — "Evidence Ledger"

Use an editorial/administrative visual system inspired by:
- government records
- engineering drawings
- field inspection sheets
- map annotations
- audit registers
- redacted documents
- statistical workpapers

The UI should feel assembled from **layers of evidence**, not a collection of SaaS cards.

## 3. Typography

Use a distinctive but practical combination.

### Recommended
- **Headings:** IBM Plex Sans / IBM Plex Serif
- **Body:** Source Sans 3
- **Numbers / IDs / technical metadata:** IBM Plex Mono

Do not use Inter.

Hierarchy:
- page title: 32–40px
- section title: 20–24px
- body: 14–16px
- metadata: 11–13px
- table text: 13–14px

Use sentence case. Avoid excessive uppercase.

## 4. Color System

Use a restrained paper-and-ink palette.

```text
Canvas:          warm off-white
Surface:         paper white
Ink:             charcoal
Muted ink:       slate
Rule lines:      warm gray
Primary accent:  deep indigo / archival blue
Attention:       amber
Critical:        muted vermilion
Positive:        forest green
Map accent:      restrained blue/green
```

Status colors should be used as **signals**, not decoration.

Avoid gradients entirely.

## 5. Layout

Use a left navigation rail and a wide working canvas.

```text
┌─────────────┬─────────────────────────────────────────────────────┐
│ DRISHTI     │ Command Center                                    │
│             │                                                     │
│ Overview    │ Summary strip                                      │
│ Queue       │ ─────────────────────────────────────────────────── │
│ Projects    │                                                     │
│ Cases       │ Main analytical area          Investigation queue   │
│ Reports     │                                                     │
│ Rules       │                                                     │
│             │                                                     │
│ Data        │                                                     │
└─────────────┴─────────────────────────────────────────────────────┘
```

Navigation should remain quiet. The content area carries visual emphasis.

## 6. Command Center

Do not make six giant KPI cards.

Instead use a **summary strip**:

```text
WORKS  4,821     VALUE  ₹186.4 Cr     HIGH  47     DELAYED  132
```

Below it:
- left: geographic distribution
- center: risk trend / distribution
- right: compact investigation queue

Use thin dividers and strong typographic hierarchy.

## 7. Investigation Queue

The queue should feel like a professional work register.

Use:
- dense rows
- fixed column alignment
- subtle row separators
- small priority markers
- inline signal labels
- sticky table header

Example:

```text
!  MPL-10281   Community Hall     X     HIGH
   Cost +60% · F/P gap 52pp · Delay 145d

   MPL-10412   Water Tank         Y     HIGH
   Duplicate candidate · Delay
```

Do not put every row inside a rounded card.

## 8. Project Intelligence Page

This is the signature screen.

### Header
Use a strong horizontal identity:

```text
MPL-10281
Construction of Community Hall
District X · Community Infrastructure

HIGH INVESTIGATION PRIORITY
4 SIGNALS CONVERGE
```

### Evidence layout

Use an evidence ledger:

```text
SIGNAL                 OBSERVED        REFERENCE        DELTA
────────────────────────────────────────────────────────────
Financial / Physical   84% / 32%       —                +52 pp
Cost                   ₹38.7L           ₹24.2L median    +60%
Duration               510 days         365 days         +145d
Duplicate similarity   91%              —                43m away
```

This is more distinctive than four colored cards.

## 9. Rule → Evidence → Action

Every important alert should visually follow:

```text
RULE
Financial / physical mismatch

EVIDENCE
Financial progress is 84%.
Physical progress is 32%.
Difference: 52 percentage points.

ACTION
Verify physical execution and
payment milestones.
```

Use a left-side rule marker and horizontal progression rather than three separate boxes.

## 10. Risk Visualization

Avoid a giant circular gauge.

Use a **signal stack**:

```text
INVESTIGATION PRIORITY

████████████████░░░░  HIGH

4 independent signals
Cost anomaly
Progress mismatch
Delay
Duplicate candidate
```

The important information is the evidence count and reasons, not a decorative score.

## 11. Map Design

Use Leaflet with a restrained basemap.

Map markers should encode:
- priority
- project type
- status

Avoid dozens of oversized pins.

Clicking a marker should open a narrow information panel rather than a large floating card.

## 12. Charts

Prefer:
- horizontal bars
- small multiples
- time-series lines
- distribution plots
- geographic density
- compact comparison bars

Avoid:
- 3D charts
- donut charts for everything
- rainbow charts
- unnecessary animation

## 13. Tables

Tables are a first-class interface.

Use:
- numeric alignment
- monospace IDs
- right-aligned currency
- compact row height
- sticky headers
- visible filter state
- keyboard-friendly navigation

## 14. Interaction

Motion should explain state changes.

Use:
- 150–250ms transitions
- subtle row highlight on selection
- skeleton loading
- inline expansion for evidence
- drawer for secondary detail

Avoid:
- page-wide animations
- bouncing elements
- animated gradients
- excessive hover effects

## 15. Icons

Use Lucide or another restrained line-icon system.

Icons should clarify actions:
- investigate
- verify
- compare
- escalate
- export
- filter
- location
- timeline

Never use icons merely to fill empty space.

## 16. Forms

Forms should resemble administrative work forms:
- clear labels
- visible required fields
- short helper text
- validation beside the field
- minimal decorative containers

## 17. Report Preview

Make the report preview look like an official investigation document:
- document title
- case/project identifier
- evidence table
- peer benchmark
- chronology
- verification checklist
- officer remarks
- status
- generated timestamp

## 18. Accessibility

- WCAG-conscious contrast.
- Never communicate status using color alone.
- Keyboard navigation for tables and actions.
- Visible focus states.
- Meaningful labels for charts.
- Minimum comfortable touch targets.

## 19. Responsive Behavior

Desktop is the primary environment.

Tablet:
- collapse navigation
- preserve queue readability
- stack secondary panels

Mobile:
- prioritize project intelligence and case actions
- replace wide tables with structured rows
- preserve evidence hierarchy

## 20. Design Test

Before shipping a screen, ask:

1. Does it look like an investigation tool rather than an AI template?
2. Can an officer understand what needs attention within five seconds?
3. Is every visual element carrying information?
4. Are evidence and provenance more prominent than decoration?
5. Could the screen still look credible if all color were removed?

If the answer to #5 is no, the design is probably relying too much on decoration.
