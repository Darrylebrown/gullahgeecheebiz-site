# GGB Autonomous Publishing Agents — Architecture

## Two Agents, One Trust

The 5 pipeline bots (validator → repairer → stager → previewer → readiness) handle the mechanical in-betweens. They never submit, never decide, never touch a live platform.

These two agents are different. They have reasoning, writing, creativity, management, contract judgment, and — critically — the owner's trust to push buttons.

---

## Agent A: PUBLISHER PRIME (The Strategist)

**Role:** Decides what to publish, when, and on which terms. Manages the queue. Reviews readiness. Makes judgment calls. Delegates execution.

**Capabilities:**

| Domain | Skill |
|--------|-------|
| Reasoning | Evaluates readiness reports, detects edge cases, decides whether to proceed or hold |
| Writing | Crafts descriptions, keywords, categories, marketing copy, rights declarations |
| Creativity | Suggests better categories, keywords, pricing tiers, bundling opportunities |
| Management | Prioritizes queue, manages dependencies, tracks multiple titles, handles conflicts |
| Documents | Reviews manifests, metadata packages, rights files, AI disclosures |
| Contracts | Understands territories, publishing rights, KDP Select terms, AI disclosure requirements, copyright law |
| Autonomy | Works without supervision, reports decisions, escalates only when blocked |

**Workflow:**

1. Scans for newly discovered packages
2. Reviews validator/repairer/stager/previewer results
3. Makes judgment calls on metadata, categories, pricing, rights
4. Approves or rejects for submission
5. Delegates to Agent B for platform execution
6. Monitors submission status
7. Reports to owner

**Safety rules (hard-coded, cannot override):**
- Never publish without owner's explicit `publish now` command
- Never modify Blood Remembers price
- Never touch In Review or Live titles
- Never create duplicate Sweetgrass draft
- Default KDP Select OFF, No DRM
- One title at a time
- Oldest validated first

---

## Agent B: SUBMISSION SPECIALIST (The Executor)

**Role:** Handles platform-specific upload, processing monitoring, previewer verification, and submission execution. The button pusher.

**Capabilities:**

| Domain | Skill |
|--------|-------|
| Reasoning | Verifies draft identity, detects processing errors, decides retry vs escalate |
| Writing | Fills platform forms, maps metadata fields, writes platform-specific descriptions |
| Creativity | Adapts to platform quirks, finds workarounds for UI limitations |
| Management | Tracks upload progress, manages retries, resumes after interruption |
| Documents | Uploads manuscripts, covers, audio files; verifies hashes post-upload |
| Contracts | Reads platform terms, confirms rights selections, verifies AI disclosure fields |
| Autonomy | Runs browser automation, monitors processing, captures preview evidence, submits on approval |

**Workflow:**

1. Receives approved manifest from Agent A
2. Authenticates with platform (browser session)
3. Locates or creates draft
4. Verifies draft identity matches manifest
5. Uploads files (manuscript, cover, audio)
6. Monitors processing
7. Launches previewer, captures evidence
8. Saves draft (stop-before-submit)
9. Reports readiness back to Agent A
10. On owner `publish now`: submits exactly one title

**Safety rules (hard-coded, cannot override):**
- Never submit without Agent A's signed approval
- Never submit without owner's `publish now`
- Verify draft ID before every write
- Stop-before-submit is default
- Screenshot and log every step
- Retry max 3 times, then escalate

---

## Trust Model

```
Owner ──publish now──→ Agent A ──approved manifest──→ Agent B ──submit──→ Platform
                           ↑                                │
                           └── evidence, status ────────────┘
```

- Agent A cannot submit to platforms directly
- Agent B cannot approve or decide what to publish
- Both agents log every action to the audit trail
- Owner can revoke trust at any time
- Both agents are bound by the same safety invariants as the control plane

---

## Implementation

Both agents are implemented as Hermes agent skills that load the publisher control plane and add reasoning, writing, and platform interaction layers.

They run as cron jobs or on-demand via `delegate_task`.

Agent B requires:
- Playwright with persistent browser profile (KDP session)
- Owner's authenticated browser (no password capture)
- Screenshot capture capability
- File upload through browser input APIs
