# GGB Disaster Recovery Plan
_Generated: 2026-08-30T07:57:35.029689_

## 1. Backup cadence
- **Code + configs**: daily via `headquarters/backup.sh` (AES-256-CBC)
- **Databases**: on every write-batch; encrypted with `encrypt_db.sh`
- **Keys**: `.agent_tokens.env`, `.ggb_db_key`, `.ggb_backup_key` stored offline
  (password manager + printed paper in safe).

## 2. Recovery procedure (RTO target: 30 min)
1. Provision clean macOS host with Xcode CLT + Python 3.11+.
2. Clone repo: `git clone <private-url> ggb-engine && cd ggb-engine`.
3. Decrypt latest backup: `headquarters/decrypt_db.sh <file>.enc <file>`.
4. Rebuild `.env` from offline key store; `chmod 600 .env*`.
5. Start agents in order: Royalty Dashboard → Publishing Controller →
   Bot Factory → Universal Submitter.
6. Verify with `python3 headquarters/security-hardening.py` (target score ≥ 80).

## 3. Rotation schedule
See `security-reports/secrets-rotation-schedule.json`.

## 4. Contacts
- Security lead: _TODO_
- Infra lead: _TODO_
- Legal/compliance: _TODO_

## 5. Test the plan
Quarterly tabletop + annual full restore drill.
