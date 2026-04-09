"""
Metrics collection — SSL, response time, bandwidth, CPU, memory, DB speed.
"""
import datetime
import ssl
import socket
import time

from models.config import HAS_REQUESTS

if HAS_REQUESTS:
    import requests


def collect_subdomain_metrics(domain, ssh_manager):
    """
    Collect SSL, uptime, response time, bandwidth, DB speed, CPU/memory
    for *domain* and return a dict.

    *ssh_manager* is a ``models.ssh_client.SSHClientManager`` instance used
    to gather server-side stats.
    """
    metrics = {
        "ssl_status": "Unknown",
        "ssl_expiry_days": 0,
        "ssl_expiry_date": "",
        "response_time_ms": 0,
        "uptime_pct": 0,
        "bandwidth_kbps": 0,
        "db_speed_ms": 0,
        "cpu_pct": 0,
        "memory_pct": 0,
    }


    try:
        ctx = ssl.create_default_context()
        with ctx.wrap_socket(socket.socket(), server_hostname=domain) as s:
            s.settimeout(5)
            s.connect((domain, 443))
            cert = s.getpeercert()
            expire_str = cert.get("notAfter", "")
            expire_date = datetime.datetime.strptime(expire_str, "%b %d %H:%M:%S %Y %Z")
            days_left = (expire_date - datetime.datetime.utcnow()).days
            metrics["ssl_expiry_days"] = max(days_left, 0)
            metrics["ssl_expiry_date"] = expire_date.strftime("%Y-%m-%d")
            metrics["ssl_status"] = "Valid" if days_left > 0 else "Expired"
    except Exception:
        metrics["ssl_status"] = "No SSL"
        metrics["ssl_expiry_days"] = 0


    if HAS_REQUESTS:
        try:
            start = time.time()
            resp = requests.get(
                f"http://{domain}", timeout=8, verify=False, allow_redirects=True
            )
            elapsed_ms = (time.time() - start) * 1000
            metrics["response_time_ms"] = round(elapsed_ms, 1)
            content_bytes = len(resp.content)
            elapsed_sec = max(elapsed_ms / 1000, 0.001)
            metrics["bandwidth_kbps"] = round(
                (content_bytes * 8) / elapsed_sec / 1000, 1
            )
            metrics["uptime_pct"] = 100 if resp.status_code < 500 else 0
        except Exception:
            metrics["response_time_ms"] = 0
            metrics["uptime_pct"] = 0
            metrics["bandwidth_kbps"] = 0


    try:
        client = ssh_manager.connect()
        try:
            metrics["cpu_pct"] = ssh_manager.get_cpu_for_domain(client, domain)
            metrics["memory_pct"] = ssh_manager.get_memory_for_domain(client, domain)
            metrics["db_speed_ms"] = ssh_manager.get_db_speed(client)
        finally:
            client.close()
    except Exception:
        pass

    return metrics
