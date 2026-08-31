# GGB Disaster Recovery Plan
Generated: 2026-08-31 16:24 UTC

## System Overview
- 370+ agents across 29 systems
- 9 live platforms on localhost (:8080-8091)
- 1,817 books in SQLite database
- 54 cron jobs
- GitHub Pages site at gullahgeecheebiz.com

## Critical Data Locations
- Database: /Users/darrylsmac/gullahgeecheebiz-site/publish/publisher.db
- Environment: /Users/darrylsmac/gullahgeecheebiz-site/.env
- Agent configs: /Users/darrylsmac/gullahgeecheebiz-site/ggb-engine/headquarters/agents/
- Security state: /Users/darrylsmac/gullahgeecheebiz-site/ggb-engine/headquarters/logs/security-network/
- Royalty data: /Users/darrylsmac/gullahgeecheebiz-site/ggb-engine/headquarters/logs/royalty-dashboard/

## Recovery Steps
1. Restore database from backup
2. Restore .env from secure storage
3. Start services in order:
   a. Command Center (:8080)
   b. Universal Submitter (:8086)
   c. Publishing Controller (:8090)
   d. Bot Factory (:8091)
   e. All other services
4. Verify all 9 platforms respond
5. Run smoke tests: cd /Users/darrylsmac/gullahgeecheebiz-site && npm test

## Contact
- Primary: Darryl Elliott Brown
- System: Hermes Agent (self-healing)

## Backup Schedule
- Database: Daily via cron
- Configs: Weekly via git
- Logs: 30-day retention
