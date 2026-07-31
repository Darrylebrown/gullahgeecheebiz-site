# GGB Publisher Control Plane — Architecture

## Overview

The GGB Publisher Control Plane coordinates publishing across KDP, ACX, Draft2Digital, Spotify, and DistroKid. It integrates with the existing GGB Engine, Buffer, and Hub to provide a safe, traceable, owner-controlled publishing workflow.

## System Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    GGB Publisher Control Plane                │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐ │
│  │ Discover │→│ Reconcile│→│  Audit   │→│   Repair   │ │
│  └──────────┘  └──────────┘  └──────────┘  └────────────┘ │
│       ↓            ↓             ↓              ↓          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐ │
│  │  Stage   │→│ Preview  │→│ Approve  │→│  Submit    │ │
│  └──────────┘  └──────────┘  └──────────┘  └────────────┘ │
│       ↓            ↓             ↓              ↓          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐ │
│  │  Status  │→│ Resume   │→│ Manifest │→│  Registry   │ │
│  └──────────┘  └──────────┘  └──────────┘  └────────────┘ │
└─────────────────────────────────────────────────────────────┘
       │            │             │              │
       ↓            ↓             ↓              ↓
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐
│  GitHub  │  │ Airtable │  │  Notion  │  │  Platform  │
│ (Source) │  │ (Status) │  │ (Docs)   │  │ (KDP/ACX) │
└──────────┘  └──────────┘  └──────────┘  └────────────┘
```

## State Machine

```
DISCOVERED → PACKAGED → VALIDATING → BLOCKED or VALIDATED
→ STAGED → PLATFORM_UPLOADED → PLATFORM_PROCESSED
→ PREVIEW_CLEAN → AWAITING_OWNER_APPROVAL
→ APPROVED → SUBMITTED → IN_REVIEW → LIVE

Also: REJECTED, NEEDS_REVISION, WITHDRAWN, ARCHIVED
```

## Components

### 1. Release Manifest (`schemas/release-manifest.json`)
- JSON Schema v2020-12
- UUID v4 manifest ID
- SHA-256 artifact hashes
- Full metadata, rights, publishing, validation, approval, and submission tracking
- Versioned for migration support

### 2. Artifact Registry (`publish/registry/registry.jsonl`)
- Append-only JSONL log
- SHA-256 hash verification
- Duplicate detection by hash
- MIME type classification
- Provenance tracking

### 3. Validator
- Cover: dimensions, aspect ratio, color mode
- Metadata: description length, keywords, categories, AI disclosure
- Rights: publishing rights, price safeguards, protected titles
- Hashes: file integrity verification
- Schema: required field completeness

### 4. Repair Engine
- Cover color mode conversion (CMYK → RGB)
- Cover size upscaling (minimum 1000×625)
- Works on derivative copies only
- Maximum 3 repair-and-test attempts
- Before/after hash recording

### 5. Platform Adapters
- Common interface: check_auth, find_draft, upload_files, check_processing, save_draft, submit, get_status
- KDP adapter: browser automation with persistent profile (Phase 2)
- ACX, D2D, Spotify, DistroKid: Phase 3

### 6. CLI (`ggb publish`)
- discover, reconcile, audit, repair, stage, preview, manifest, approve, submit, status, resume
- --dry-run, --json, --trace support
- Structured JSON and human-readable output
- Idempotent operations

## Price Safeguards
- Sweetgrass: $3.99 (enforced)
- Encyclopedia Vol 01: $9.99 (enforced)
- Blood Remembers: never modify
- All other prices: owner approval required

## Safety Rules
- Never publish without explicit owner approval
- Never create duplicate listings
- Never touch live ASINs or In Review titles
- Never modify protected prices
- Never bulk Select-all
- Never guess legal declarations
- Never overwrite originals
- Never expose secrets
- Default DRM: No
- Default KDP Select: Off

## File Locations
```
gullahgeecheebiz-site/ggb-engine/
├── publisher.py          # Main control plane
├── schemas/
│   └── release-manifest.json
├── publish/
│   ├── registry/         # Artifact registry (JSONL)
│   ├── manifests/        # Release manifests (JSON)
│   ├── logs/             # Workflow logs
│   ├── state/            # State machine persistence
│   ├── staging/          # Staged upload files
│   └── repairs/          # Derivative repair copies
└── ARCHITECTURE.md
```

## CLI Usage
```bash
# Discover a publishing package
python3 publisher.py discover ~/gullah-geechee-project/packaged/vol-01-historiography/

# Full workflow
python3 publisher.py reconcile <manifest_id>
python3 publisher.py audit <manifest_id>
python3 publisher.py stage <manifest_id>
python3 publisher.py preview <manifest_id>
python3 publisher.py approve <manifest_id>
python3 publisher.py status <manifest_id>
python3 publisher.py submit <manifest_id>

# JSON output
python3 publisher.py --json audit <manifest_id>

# Resume after interruption
python3 publisher.py resume <manifest_id>
```

## Testing
- Manifest schema validation
- State transition enforcement
- Price safeguard enforcement
- Protected title detection
- Cover validation
- Metadata completeness
- Hash integrity
- Repair idempotency
- Approval invalidation after artifact changes
- Duplicate prevention
- Queue ordering

## Security
- Least privilege design
- Secrets in approved storage only
- No credential logging
- Approvals bound to artifact hashes
- Append-only audit trail
- Short-lived signed actions
- Threat model covers: browser automation, file uploads, approval links, connectors, supply chain

## Known Limitations (Phase 1)
- KDP browser upload bridge not yet implemented (Phase 2)
- ACX, D2D, Spotify, DistroKid adapters not yet implemented (Phase 3)
- Airtable operational sync not yet implemented (Phase 3)
- Owner approval console is CLI-only (web UI in Phase 2)
- EPUBCheck requires external tool installation
- No monitoring/alerting yet (Phase 4)
