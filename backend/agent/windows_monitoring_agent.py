import os
import time
import platform
import socket

import psutil
import requests


# ==========================================
# CONFIGURATION
# ==========================================

API_URL = "http://127.0.0.1:8000/api/asset-metrics/"

ORGANIZATION_ID = 6
ASSET_ID = 7

COLLECTION_INTERVAL = 60


# ==========================================
# COLLECT SYSTEM METRICS
# ==========================================

def collect_metrics():

    # CPU usage
    cpu_usage = psutil.cpu_percent(interval=1)

    # Memory usage
    memory_usage = psutil.virtual_memory().percent

    # Disk usage
    system_drive = os.environ.get("SystemDrive", "C:")
    disk_usage = psutil.disk_usage(system_drive + "\\").percent

    # Network usage over a one-second interval
    network_before = psutil.net_io_counters()

    time.sleep(1)

    network_after = psutil.net_io_counters()

    network_in = (
        network_after.bytes_recv - network_before.bytes_recv
    )

    network_out = (
        network_after.bytes_sent - network_before.bytes_sent
    )

    return {
        "organization_id": ORGANIZATION_ID,
        "asset_id": ASSET_ID,
        "cpu_usage": round(cpu_usage, 2),
        "memory_usage": round(memory_usage, 2),
        "disk_usage": round(disk_usage, 2),
        "network_in": round(network_in, 2),
        "network_out": round(network_out, 2),
        "additional_metrics": {
            "source": "windows_monitoring_agent",
            "hostname": socket.gethostname(),
            "operating_system": platform.platform(),
            "network_unit": "bytes_per_second",
            "agent_version": "1.0"
        }
    }


# ==========================================
# SEND METRICS TO CYBERRISK API
# ==========================================

def send_metrics(metrics):

    try:

        response = requests.post(
            API_URL,
            json=metrics,
            timeout=10
        )

        response.raise_for_status()

        result = response.json()

        print(
            f"[SUCCESS] Metrics saved. "
            f"Metric ID: {result['metric_id']}"
        )

        print(
            f"CPU: {metrics['cpu_usage']}% | "
            f"Memory: {metrics['memory_usage']}% | "
            f"Disk: {metrics['disk_usage']}%"
        )

        print(
            f"Network In: {metrics['network_in']} bytes/s | "
            f"Network Out: {metrics['network_out']} bytes/s"
        )

    except requests.exceptions.RequestException as error:

        print(f"[ERROR] Could not send metrics: {error}")


# ==========================================
# MAIN MONITORING LOOP
# ==========================================

def start_monitoring():

    print("=" * 55)
    print("CYBERRISK WINDOWS MONITORING AGENT")
    print("=" * 55)

    print(f"Organization ID: {ORGANIZATION_ID}")
    print(f"Asset ID: {ASSET_ID}")
    print(f"Collection Interval: {COLLECTION_INTERVAL} seconds")
    print("Monitoring started. Press CTRL+C to stop.")
    print("=" * 55)

    while True:

        try:

            metrics = collect_metrics()

            send_metrics(metrics)

            time.sleep(COLLECTION_INTERVAL)

        except KeyboardInterrupt:

            print("\nMonitoring agent stopped.")
            break

        except Exception as error:

            print(f"[ERROR] Monitoring failed: {error}")
            time.sleep(COLLECTION_INTERVAL)


if __name__ == "__main__":
    start_monitoring()
