#!/usr/bin/env python3
"""Phase 0: Environmental Forensics - System Baseline Capture"""
import json
import os
import subprocess
import sys
from datetime import datetime


def run_command(cmd, output_file):
    """Run a command and save output to file."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=30
        )
        with open(output_file, "w") as f:
            f.write(f"Command: {cmd}\n")
            f.write(f"Exit Code: {result.returncode}\n")
            f.write(f"STDOUT:\n{result.stdout}\n")
            if result.stderr:
                f.write(f"STDERR:\n{result.stderr}\n")
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        with open(output_file, "w") as f:
            f.write(f"Command: {cmd}\n")
            f.write("ERROR: Command timed out after 30 seconds\n")
        return False
    except Exception as e:
        with open(output_file, "w") as f:
            f.write(f"Command: {cmd}\n")
            f.write(f"ERROR: {str(e)}\n")
        return False


def main():
    bug_dir = os.getenv("BUG_DIR", "/tmp/hbc_bugs_default")
    os.makedirs(f"{bug_dir}/baseline", exist_ok=True)

    print("=== PHASE 0: ENVIRONMENTAL FORENSICS ===\n")

    baseline = {"timestamp": datetime.utcnow().isoformat() + "Z", "system_state": {}}

    # Capture Docker state
    print("Capturing Docker state...")
    run_command("docker compose ps", f"{bug_dir}/baseline/docker_ps.txt")
    run_command("docker stats --no-stream", f"{bug_dir}/baseline/docker_stats.txt")

    # Capture logs
    print("Capturing Docker logs...")
    run_command("docker compose logs --tail=500", f"{bug_dir}/baseline/all_logs.txt")

    # Capture process list
    print("Capturing process list...")
    run_command("ps aux", f"{bug_dir}/baseline/processes.txt")

    # Capture network ports
    print("Capturing network ports...")
    run_command(
        "netstat -tuln 2>/dev/null || ss -tuln", f"{bug_dir}/baseline/ports.txt"
    )

    # Check service health
    print("Checking service health...")
    services = {
        "frontend": "http://localhost:3100",
        "backend": "http://localhost:8100",
        "grafana": "http://localhost:3001",
        "prometheus": "http://localhost:9090",
    }

    health_status = {}
    for service, url in services.items():
        try:
            import requests

            response = requests.get(
                f"{url}/health" if service != "prometheus" else f"{url}/-/healthy",
                timeout=5,
            )
            health_status[service] = {
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "status_code": response.status_code,
            }
        except:
            health_status[service] = {"status": "unreachable", "status_code": None}

    baseline["system_state"]["services"] = health_status

    # Save baseline
    with open(f"{bug_dir}/baseline/system_baseline.json", "w") as f:
        json.dump(baseline, f, indent=2)

    print(f"\nBaseline captured: {bug_dir}/baseline/")
    print("Services status:")
    for service, status in health_status.items():
        print(f"  {service}: {status['status']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
