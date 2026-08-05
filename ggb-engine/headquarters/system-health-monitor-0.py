import requests
import time
import psutil
import json
import logging
import os
import subprocess
from datetime import datetime, timedelta
from threading import Thread
from http.server import SimpleHTTPRequestHandler, HTTPServer
import signal
import sys

# --- Configuration ---
LOG_DIR = "/Users/darrylsmac/gullahgeecheebiz-site/ggb-engine/headquarters/logs/health-monitor/"
HEALTH_SCORE_FILE = "/Users/darrylsmac/gullahgeecheebiz-site/ggb-engine/headquarters/health_score.json"
ALERT_LOG_FILE = "/Users/darrylsmac/gullahgeecheebiz-site/ggb-engine/headquarters/logs/health-monitor/health-alerts.log"
PLATFORMS = {
    "platform1": {"port": 8080, "health_endpoint": "/health", "pid_file": "/var/run/ggb_platform1.pid", "restart_cmd": "systemctl restart ggb_platform1"},
    "platform2": {"port": 8081, "health_endpoint": "/health", "pid_file": "/var/run/ggb_platform2.pid", "restart_cmd": "systemctl restart ggb_platform2"},
    "platform3": {"port": 8082, "health_endpoint": "/health", "pid_file": "/var/run/ggb_platform3.pid", "restart_cmd": "systemctl restart ggb_platform3"},
    "platform4": {"port": 8083, "health_endpoint": "/health", "pid_file": "/var/run/ggb_platform4.pid", "restart_cmd": "systemctl restart ggb_platform4"},
    "platform5": {"port": 8084, "health_endpoint": "/health", "pid_file": "/var/run/ggb_platform5.pid", "restart_cmd": "systemctl restart ggb_platform5"},
    "platform6": {"port": 8085, "health_endpoint": "/health", "pid_file": "/var/run/ggb_platform6.pid", "restart_cmd": "systemctl restart ggb_platform6"},
    "platform7": {"port": 8086, "health_endpoint": "/health", "pid_file": "/var/run/ggb_platform7.pid", "restart_cmd": "systemctl restart ggb_platform7"},
    "platform8": {"port": 8087, "health_endpoint": "/health", "pid_file": "/var/run/ggb_platform8.pid", "restart_cmd": "systemctl restart ggb_platform8"},
    "platform9": {"port": 8088, "health_endpoint": "/health", "pid_file": "/var/run/ggb_platform9.pid", "restart_cmd": "systemctl restart ggb_platform9"},
}
CHECK_INTERVAL_SECONDS = 60
AUTO_HEAL_THRESHOLD = 3 # Number of consecutive 5xx errors before restart
DASHBOARD_PORT = 8092
CRON_JOB_LOG_DIR = "/var/log/cron_jobs/" # Assuming cron jobs log their last run time here

# --- Global State ---
platform_error_counts = {name: 0 for name in PLATFORMS}
platform_status_history = {name: [] for name in PLATFORMS} # Stores last N statuses for dashboard
HEALTH_EVENTS = [] # Stores recent health events for the dashboard
MAX_HEALTH_EVENTS = 50

# --- Setup Logging ---
os.makedirs(LOG_DIR, exist_ok=True)

# Main logger for health monitor activities
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "system_health_monitor.log")),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('HealthMonitor')

# Separate logger for alerts
alert_logger = logging.getLogger('HealthAlerts')
alert_logger.setLevel(logging.WARNING)
alert_handler = logging.FileHandler(ALERT_LOG_FILE)
alert_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
alert_handler.setFormatter(alert_formatter)
alert_logger.addHandler(alert_handler)
alert_logger.propagate = False # Prevent alerts from going to the main logger

def log_alert(message):
    """Logs an alert message to the alert log file."""
    alert_logger.warning(message)
    add_health_event(f"ALERT: {message}", "critical")

def add_health_event(message, level="info"):
    """Adds a health event to the in-memory list for the dashboard."""
    global HEALTH_EVENTS
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    HEALTH_EVENTS.insert(0, {"timestamp": timestamp, "message": message, "level": level})
    HEALTH_EVENTS = HEALTH_EVENTS[:MAX_HEALTH_EVENTS]

# --- Platform Monitoring Functions ---
def check_platform_health(name, config):
    """Checks the health of a single platform."""
    url = f"http://127.0.0.1:{config['port']}{config['health_endpoint']}"
    status = "unknown"
    response_time = "N/A"
    platform_info = {}
    try:
        start_time = time.time()
        response = requests.get(url, timeout=5)
        end_time = time.time()
        response_time = f"{(end_time - start_time):.3f}s"
        platform_info = response.json() if response.content else {}

        if 200 <= response.status_code < 300:
            status = "ok"
            platform_error_counts[name] = 0
            logger.info(f"Platform {name} ({config['port']}) health check OK. Response time: {response_time}")
            add_health_event(f"Platform {name} healthy.", "info")
        elif 500 <= response.status_code < 600:
            status = "error"
            platform_error_counts[name] += 1
            log_alert(f"Platform {name} ({config['port']}) returned 5xx error (Status: {response.status_code}). Consecutive errors: {platform_error_counts[name]}")
            add_health_event(f"Platform {name} returned 5xx error ({response.status_code}).", "warning")
            if platform_error_counts[name] >= AUTO_HEAL_THRESHOLD:
                logger.error(f"Platform {name} ({config['port']}) reached {AUTO_HEAL_THRESHOLD} consecutive 5xx errors. Attempting restart.")
                log_alert(f"Auto-healing: Restarting platform {name} due to {AUTO_HEAL_THRESHOLD} consecutive 5xx errors.")
                add_health_event(f"Auto-healing: Restarting platform {name}.", "critical")
                restart_platform(name, config['restart_cmd'])
                platform_error_counts[name] = 0 # Reset count after restart attempt
        else:
            status = "warning"
            logger.warning(f"Platform {name} ({config['port']}) health check WARNING (Status: {response.status_code}). Response: {response.text[:100]}")
            add_health_event(f"Platform {name} returned non-2xx status ({response.status_code}).", "warning")

    except requests.exceptions.ConnectionError:
        status = "down"
        platform_error_counts[name] += 1
        log_alert(f"Platform {name} ({config['port']}) is DOWN (Connection Error). Consecutive errors: {platform_error_counts[name]}")
        add_health_event(f"Platform {name} is DOWN (Connection Error).", "critical")
        if platform_error_counts[name] >= AUTO_HEAL_THRESHOLD:
            logger.error(f"Platform {name} ({config['port']}) is down for {AUTO_HEAL_THRESHOLD} consecutive checks. Attempting restart.")
            log_alert(f"Auto-healing: Restarting platform {name} due to {AUTO_HEAL_THRESHOLD} consecutive 'down' statuses.")
            add_health_event(f"Auto-healing: Restarting platform {name}.", "critical")
            restart_platform(name, config['restart_cmd'])
            platform_error_counts[name] = 0
    except requests.exceptions.Timeout:
        status = "timeout"
        platform_error_counts[name] += 1
        log_alert(f"Platform {name} ({config['port']}) health check TIMEOUT. Consecutive errors: {platform_error_counts[name]}")
        add_health_event(f"Platform {name} health check TIMEOUT.", "warning")
    except json.JSONDecodeError:
        status = "invalid_json"
        platform_error_counts[name] += 1
        logger.warning(f"Platform {name} ({config['port']}) returned non-JSON response.")
        add_health_event(f"Platform {name} returned non-JSON response.", "warning")
    except Exception as e:
        status = "error"
        platform_error_counts[name] += 1
        log_alert(f"An unexpected error occurred while checking platform {name}: {e}")
        add_health_event(f"Unexpected error checking {name}: {e}", "critical")
    finally:
        # Keep track of recent statuses for the dashboard
        platform_status_history[name].append({"status": status, "timestamp": datetime.now().isoformat()})
        # Keep only the last 10 statuses for a quick trend
        platform_status_history[name] = platform_status_history[name][-10:]
    return {"status": status, "response_time": response_time, "info": platform_info}

def restart_platform(name, restart_cmd):
    """Attempts to restart a platform using its configured command."""
    logger.info(f"Executing restart command for {name}: {restart_cmd}")
    try:
        # Assuming restart_cmd is a systemctl command or similar
        # For security, ensure restart_cmd is well-defined and trusted
        result = subprocess.run(restart_cmd, shell=True, check=True, capture_output=True, text=True)
        logger.info(f"Restart command for {name} successful: {result.stdout}")
        add_health_event(f"Platform {name} restart initiated successfully.", "info")
    except subprocess.CalledProcessError as e:
        log_alert(f"Failed to restart platform {name} with command '{restart_cmd}': {e.stderr}")
        add_health_event(f"Failed to restart platform {name}.", "critical")
    except Exception as e:
        log_alert(f"Error during restart attempt for platform {name}: {e}")
        add_health_event(f"Error during restart attempt for platform {name}: {e}", "critical")

# --- System Resource Monitoring ---
def get_system_resources():
    """Retrieves current CPU, memory, disk, and network usage."""
    cpu_percent = psutil.cpu_percent(interval=1) # Blocking call, takes 1 second
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/') # Monitor root partition
    network_io = psutil.net_io_counters()

    return {
        "cpu_percent": cpu_percent,
        "memory_percent": memory.percent,
        "memory_total_gb": round(memory.total / (1024**3), 2),
        "memory_used_gb": round(memory.used / (1024**3), 2),
        "disk_percent": disk.percent,
        "disk_total_gb": round(disk.total / (1024**3), 2),
        "disk_used_gb": round(disk.used / (1024**3), 2),
        "network_bytes_sent": network_io.bytes_sent,
        "network_bytes_recv": network_io.bytes_recv,
    }

# --- Cron Job Monitoring ---
def monitor_cron_jobs():
    """
    Monitors all 55 cron jobs.
    This assumes cron jobs log their last run time to specific files in CRON_JOB_LOG_DIR
    or that `cron-health-checker.py` is run separately and provides this data.
    For this script, we'll simulate based on `cron-health-checker.py` output.
    """
    cron_health_checker_output_file = "/Users/darrylsmac/gullahgeecheebiz-site/ggb-engine/headquarters/cron_job_status.json"
    cron_status = {"status": "unavailable", "jobs": []}
    try:
        if os.path.exists(cron_health_checker_output_file):
            with open(cron_health_checker_output_file, 'r') as f:
                cron_status = json.load(f)
            logger.debug(f"Loaded cron job status from {cron_health_checker_output_file}")
            # Check for critical cron failures
            failed_jobs = [job for job in cron_status.get("jobs", []) if job.get("status") != "ok"]
            if failed_jobs:
                log_alert(f"Detected {len(failed_jobs)} cron jobs with issues: {[j['job_name'] for j in failed_jobs]}")
                add_health_event(f"Detected {len(failed_jobs)} cron jobs with issues.", "warning")
            else:
                logger.info("All cron jobs reported as OK by cron-health-checker.")
        else:
            logger.warning(f"Cron job status file not found: {cron_health_checker_output_file}. Cannot monitor cron jobs.")
            add_health_event(f"Cron job status file not found.", "warning")

    except Exception as e:
        logger.error(f"Error monitoring cron jobs from file: {e}")
        add_health_event(f"Error monitoring cron jobs: {e}", "critical")
    return cron_status

# --- Agent Monitoring (Placeholder) ---
def monitor_agents():
    """
    Monitors agent success/failure rates.
    This is a placeholder as the agent system details are not provided.
    In a real scenario, this would interact with an agent management API or log files.
    """
    agent_status = {
        "total_agents": 370,
        "active_agents": 365,
        "failed_agents_last_24h": 5,
        "success_rate_24h": "98.6%",
        "recent_failures": [
            {"agent_id": "agent_xyz", "timestamp": str(datetime.now() - timedelta(hours=1)), "reason": "Connection lost"},
            {"agent_id": "agent_abc", "timestamp": str(datetime.now() - timedelta(hours=3)), "reason": "Task failed"},
        ]
    }
    if agent_status["failed_agents_last_24h"] > 0:
        log_alert(f"{agent_status['failed_agents_last_24h']} agents reported failures in the last 24h.")
        add_health_event(f"{agent_status['failed_agents_last_24h']} agents reported failures.", "warning")
    else:
        logger.info("All agents reported healthy in the last 24h.")

    return agent_status

# --- Health Score Calculation ---
def calculate_health_score(platform_results, system_resources, cron_status, agent_status):
    """Calculates an overall health score."""
    score = 100
    deductions = []

    # Platform health
    down_platforms = [name for name, result in platform_results.items() if result["status"] in ["down", "timeout", "error"]]
    if down_platforms:
        score -= len(down_platforms) * 10
        deductions.append(f"{len(down_platforms)} platforms are down/errored.")

    # Resource usage
    if system_resources["cpu_percent"] > 90:
        score -= 5
        deductions.append("High CPU usage.")
    elif system_resources["cpu_percent"] > 70:
        score -= 2
        deductions.append("Elevated CPU usage.")

    if system_resources["memory_percent"] > 90:
        score -= 5
        deductions.append("High Memory usage.")
    elif system_resources["memory_percent"] > 70:
        score -= 2
        deductions.append("Elevated Memory usage.")

    if system_resources["disk_percent"] > 90:
        score -= 10
        deductions.append("Critical Disk space low.")
    elif system_resources["disk_percent"] > 80:
        score -= 5
        deductions.append("Low Disk space.")

    # Cron jobs
    if cron_status.get("status") == "unavailable":
        score -= 5
        deductions.append("Cron job monitoring unavailable.")
    else:
        failed_cron_jobs = [job for job in cron_status.get("jobs", []) if job.get("status") != "ok"]
        if failed_cron_jobs:
            score -= len(failed_cron_jobs) * 3
            deductions.append(f"{len(failed_cron_jobs)} cron jobs failed/missed.")

    # Agents
    if agent_status["failed_agents_last_24h"] > 0:
        score -= min(agent_status["failed_agents_last_24h"], 10) # Max 10 point deduction for agents
        deductions.append(f"{agent_status['failed_agents_last_24h']} agents reported failures.")

    score = max(0, score) # Score cannot be negative
    return {"score": score, "deductions": deductions}

# --- Main Monitoring Loop ---
def run_health_checks():
    """Executes all health checks and updates the health score."""
    logger.info("Starting health checks...")
    add_health_event("Starting system health checks.", "info")
    platform_results = {}
    for name, config in PLATFORMS.items():
        platform_results[name] = check_platform_health(name, config)

    system_resources = get_system_resources()
    cron_status = monitor_cron_jobs()
    agent_status = monitor_agents()

    health_score_data = calculate_health_score(platform_results, system_resources, cron_status, agent_status)

    full_health_report = {
        "timestamp": datetime.now().isoformat(),
        "overall_health_score": health_score_data,
        "platforms": platform_results,
        "system_resources": system_resources,
        "cron_jobs": cron_status,
        "agents": agent_status,
        "platform_status_history": platform_status_history, # For dashboard trend
        "recent_events": HEALTH_EVENTS # For dashboard events
    }

    try:
        with open(HEALTH_SCORE_FILE, 'w') as f:
            json.dump(full_health_report, f, indent=4)
        logger.info(f"Health report saved to {HEALTH_SCORE_FILE}. Score: {health_score_data['score']}/100")
    except Exception as e:
        logger.error(f"Failed to save health score to file: {e}")
        add_health_event(f"Failed to save health score to file: {e}", "critical")
    logger.info("Health checks completed.")
    return full_health_report # Return for dashboard use

# --- Dashboard Server ---
class HealthDashboardHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.path = '/health-dashboard.html'
        elif self.path == '/api/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            try:
                with open(HEALTH_SCORE_FILE, 'r') as f:
                    data = json.load(f)
                self.wfile.write(json.dumps(data, indent=4).encode('utf-8'))
            except FileNotFoundError:
                self.wfile.write(json.dumps({"error": "Health data not available"}, indent=4).encode('utf-8'))
            except Exception as e:
                self.wfile.write(json.dumps({"error": f"Failed to load health data: {e}"}, indent=4).encode('utf-8'))
            return
        
        # Serve static files from the current directory (where the script is run)
        # Ensure health-dashboard.html is in the same directory as system-health-monitor.py
        # Or you can specify a 'dashboard_root'
        try:
            super().do_GET()
        except Exception as e:
            logger.error(f"Error serving dashboard request for {self.path}: {e}")
            self.send_error(500, f"Error serving file: {e}")

    def log_message(self, format, *args):
        # Suppress HTTP server's stdout logging
        pass

def start_dashboard_server():
    """Starts a simple HTTP server to serve the health dashboard."""
    server_address = ('', DASHBOARD_PORT)
    try:
        httpd = HTTPServer(server_address, HealthDashboardHandler)
        logger.info(f"Starting health dashboard server on port {DASHBOARD_PORT}...")
        add_health_event(f"Health dashboard started on port {DASHBOARD_PORT}.", "info")
        httpd.serve_forever()
    except Exception as e:
        logger.critical(f"Failed to start dashboard server: {e}")
        add_health_event(f"Failed to start dashboard server: {e}", "critical")
        sys.exit(1)

# --- Main Execution ---
def main_loop():
    while True:
        run_health_checks()
        time.sleep(CHECK_INTERVAL_SECONDS)

def signal_handler(sig, frame):
    logger.info("Health monitor received termination signal. Shutting down gracefully.")
    add_health_event("Health monitor shutting down.", "info")
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("Starting GGB System Health Monitor.")

    # Start dashboard server in a separate thread
    dashboard_thread = Thread(target=start_dashboard_server, daemon=True)
    dashboard_thread.start()

    # Run initial check and then loop
    main_loop()