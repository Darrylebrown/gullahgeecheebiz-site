#!/bin/bash
# GGB System Health Cron Script
# Runs comprehensive system health checks
# Designed to run every 5 minutes via cron

# Configuration
BASE_DIR="/Users/darrylsmac/gullahgeecheebiz-site/ggb-engine"
HEADQUARTERS_DIR="$BASE_DIR/headquarters"
LOGS_DIR="$HEADQUARTERS_DIR/logs/cron-health"
HEALTH_SCRIPT="$HEADQUARTERS_DIR/system-health-monitor.py"
CRON_HEALTH_SCRIPT="$HEADQUARTERS_DIR/cron-health-checker.py"
ALERT_LOG="$HEADQUARTERS_DIR/health-alerts.log"

# Create logs directory
mkdir -p "$LOGS_DIR"

# Timestamp for logging
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
LOG_FILE="$LOGS_DIR/cron-health-$(date '+%Y%m%d').log"

# Function to log messages
log_message() {
    echo "[$TIMESTAMP] $1" | tee -a "$LOG_FILE"
}

# Function to send alert
send_alert() {
    echo "[$TIMESTAMP] ALERT: $1" | tee -a "$ALERT_LOG"
    log_message "ALERT: $1"
}

log_message "Starting GGB system health check"

# Check if health monitor is running
HEALTH_MONITOR_PID=$(pgrep -f "system-health-monitor.py")
if [ -z "$HEALTH_MONITOR_PID" ]; then
    send_alert "Health monitor is not running"
    
    # Try to start it
    log_message "Attempting to start health monitor"
    cd "$HEADQUARTERS_DIR"
    nohup python3 "$HEALTH_SCRIPT" > "$LOGS_DIR/health-monitor.out" 2>&1 &
    
    if [ $? -eq 0 ]; then
        log_message "Health monitor started successfully"
    else
        send_alert "Failed to start health monitor"
    fi
else
    log_message "Health monitor is running (PID: $HEALTH_MONITOR_PID)"
fi

# Check disk space
DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 90 ]; then
    send_alert "Disk usage critical: ${DISK_USAGE}%"
elif [ "$DISK_USAGE" -gt 80 ]; then
    log_message "WARNING: Disk usage high: ${DISK_USAGE}%"
else
    log_message "Disk usage normal: ${DISK_USAGE}%"
fi

# Check memory usage
MEMORY_USAGE=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
if [ "$MEMORY_USAGE" -gt 90 ]; then
    send_alert "Memory usage critical: ${MEMORY_USAGE}%"
elif [ "$MEMORY_USAGE" -gt 80 ]; then
    log_message "WARNING: Memory usage high: ${MEMORY_USAGE}%"
else
    log_message "Memory usage normal: ${MEMORY_USAGE}%"
fi

# Check CPU load
CPU_LOAD=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | sed 's/,//')
CPU_CORES=$(nproc)
CPU_THRESHOLD=$(echo "$CPU_CORES * 2" | bc)

if (( $(echo "$CPU_LOAD > $CPU_THRESHOLD" | bc -l) )); then
    send_alert "CPU load high: $CPU_LOAD (cores: $CPU_CORES)"
else
    log_message "CPU load normal: $CPU_LOAD"
fi

# Check all 9 GGB platforms
PLATFORMS=(
    "8080:Command Center"
    "8081:Book Engine"
    "8082:Content Creator"
    "8083:Social Media Manager"
    "8084:SEO Optimizer"
    "8085:Email Marketing"
    "8086:Analytics Dashboard"
    "8087:Customer Portal"
    "8088:Admin Panel"
)

OFFLINE_PLATFORMS=()

for platform in "${PLATFORMS[@]}"; do
    PORT=$(echo $platform | cut -d':' -f1)
    NAME=$(echo $platform | cut -d':' -f2)
    
    # Check if port is listening
    if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
        # Port is listening, check health endpoint
        HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:$PORT/health" --connect-timeout 5 --max-time 10)
        
        if [ "$HTTP_STATUS" = "200" ]; then
            log_message "$NAME ($PORT): Healthy"
        elif [ "$HTTP_STATUS" = "000" ]; then
            send_alert "$NAME ($PORT): Connection failed"
            OFFLINE_PLATFORMS+=("$NAME")
        else
            send_alert "$NAME ($PORT): HTTP $HTTP_STATUS"
            OFFLINE_PLATFORMS+=("$NAME")
        fi
    else
        send_alert "$NAME ($PORT): Port not listening"
        OFFLINE_PLATFORMS+=("$NAME")
    fi
done

# Summary of platform status
if [ ${#OFFLINE_PLATFORMS[@]} -eq 0 ]; then
    log_message "All platforms are healthy"
else
    send_alert "Offline platforms: ${OFFLINE_PLATFORMS[*]}"
fi

# Check SQLite database
DB_FILE="$BASE_DIR/database/ggb.db"
if [ -f "$DB_FILE" ]; then
    # Check database integrity
    INTEGRITY_CHECK=$(sqlite3 "$DB_FILE" "PRAGMA integrity_check;" 2>/dev/null)
    if [ "$INTEGRITY_CHECK" = "ok" ]; then
        log_message "Database integrity: OK"
    else
        send_alert "Database integrity check failed: $INTEGRITY_CHECK"
    fi
    
    # Check database size
    DB_SIZE=$(du -m "$DB_FILE" | cut -f1)
    log_message "Database size: ${DB_SIZE}MB"
    
    # Check book count
    BOOK_COUNT=$(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM books;" 2>/dev/null)
    if [ $? -eq 0 ]; then
        log_message "Books in database: $BOOK_COUNT"
    else
        send_alert "Failed to query books table"
    fi
else
    send_alert "Database file not found: $DB_FILE"
fi

# Run cron health checker
if [ -f "$CRON_HEALTH_SCRIPT" ]; then
    log_message "Running cron health checker"
    python3 "$CRON_HEALTH_SCRIPT" >> "$LOG_FILE" 2>&1
    
    if [ $? -eq 0 ]; then
        log_message "Cron health check completed"
    else
        send_alert "Cron health check failed"
    fi
else
    log_message "Cron health checker not found: $CRON_HEALTH_SCRIPT"
fi

# Check log file sizes (prevent them from growing too large)
LOG_SIZE_LIMIT=100  # MB
for log_file in "$LOGS_DIR"/*.log "$HEADQUARTERS_DIR"/*.log; do
    if [ -f "$log_file" ]; then
        LOG_SIZE=$(du -m "$log_file" | cut -f1)
        if [ "$LOG_SIZE" -gt "$LOG_SIZE_LIMIT" ]; then
            # Rotate log file
            mv "$log_file" "$log_file.old"
            touch "$log_file"
            log_message "Rotated large log file: $log_file (${LOG_SIZE}MB)"
        fi
    fi
done

# Network connectivity check
if ping -c 1 google.com >/dev/null 2>&1; then
    log_message "Internet connectivity: OK"
else
    send_alert "Internet connectivity: FAILED"
fi

# Check available inodes
INODE_USAGE=$(df -i / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$INODE_USAGE" -gt 90 ]; then
    send_alert "Inode usage critical: ${INODE_USAGE}%"
elif [ "$INODE_USAGE" -gt 80 ]; then
    log_message "WARNING: Inode usage high: ${INODE_USAGE}%"
else
    log_message "Inode usage normal: ${INODE_USAGE}%"
fi

# Check system uptime
UPTIME=$(uptime -p)
log_message "System uptime: $UPTIME"

# Final summary
if grep -q "ALERT" "$LOG_FILE"; then
    ALERT_COUNT=$(grep -c "ALERT" "$LOG_FILE")
    log_message "Health check completed with $ALERT_COUNT alerts"
    exit 1
else
    log_message "Health check completed successfully - all systems healthy"
    exit 0
fi