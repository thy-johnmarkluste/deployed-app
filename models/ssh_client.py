"""
SSH client wrapper — connect, execute commands, and run server.sh.
"""
import time
import paramiko

from models.security import (
    validate_domain_name,
    sanitize_for_shell,
    sanitize_path_component,
    sanitize_for_sed,
)
from models.logger import module_logger


logger = module_logger(__name__)


class SSHClientManager:
    """Thin wrapper around paramiko for the domain-connector workflow."""

    def __init__(self, hostname, username, password, timeout=10):
        self.hostname = hostname
        self.username = username
        self.password = password
        self.timeout = timeout

    def connect(self, retries=3, delay=2):
        """Return a connected paramiko.SSHClient with retry logic."""
        last_exc = None
        for attempt in range(1, retries + 1):
            try:
                client = paramiko.SSHClient()
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                client.connect(
                    hostname=self.hostname,
                    username=self.username,
                    password=self.password,
                    timeout=self.timeout,
                    banner_timeout=30,
                )
                return client
            except (paramiko.SSHException, EOFError, OSError) as e:
                last_exc = e
                if attempt < retries:
                    time.sleep(delay * attempt)
        raise last_exc

    def add_dns_entry(self, client, domain, ip):
        """Append an entry to /root/custom_dns.txt on the remote server.

        Note: This validates input as it's user-provided data."""

        is_valid, error = validate_domain_name(domain)
        if not is_valid:
            raise ValueError(f"Invalid domain: {error}")


        if not ip or not ip.strip():
            raise ValueError(f"Invalid IP: IP address cannot be empty")


        safe_domain = sanitize_for_shell(domain)
        safe_ip = sanitize_for_shell(ip)

        dns_entry = f"{safe_ip}\t{safe_domain}\n"
        command = f"echo '{dns_entry}' >> /root/custom_dns.txt"
        _stdin, _stdout, stderr = client.exec_command(command)
        error = stderr.read().decode("utf-8")
        if error:
            raise RuntimeError(error)

    def execute_server_sh(self, client, domain, log_callback=None):
        """Run ``server.sh`` for *domain* and stream output via *log_callback*.

        Note: Validates input as it's user-provided."""

        is_valid, error = validate_domain_name(domain)
        if not is_valid:
            raise ValueError(f"Invalid domain: {error}")

        safe_domain = sanitize_for_shell(domain)
        command = f"cd /root && bash server.sh {safe_domain}"
        _stdin, stdout, _stderr = client.exec_command(command, get_pty=True)
        while True:
            line = stdout.readline()
            if not line:
                break
            if log_callback:
                log_callback(line.rstrip())
        exit_status = stdout.channel.recv_exit_status()
        return exit_status

    def load_registered_entries(self, client):
        """Return list of registered domains from Apache vhost configs (deduplicated)."""
        command = (
            "for conf in /etc/apache2/sites-available/*.conf; do "
            '[ -f "$conf" ] || continue; '
            "srv=$(grep -i '^[[:space:]]*ServerName' \"$conf\" | head -n1 | awk '{print $2}'); "
            'if [ -n "$srv" ]; then echo "$srv"; fi; '
            "done | sort -u"
        )
        _stdin, stdout, _stderr = client.exec_command(command)
        output = stdout.read().decode("utf-8")
        entries = []
        seen = set()
        if output.strip():
            for line in output.strip().split("\n"):
                line = line.strip().lower()
                if line and line not in seen:
                    seen.add(line)
                    entries.append(line)
        return entries

    def load_unregistered_entries(self, client):
        """Return list of unregistered domains from custom_dns.txt."""
        command = (
            "if [ -f /root/custom_dns.txt ]; then "
            "awk '{print $2}' /root/custom_dns.txt | sort | uniq; "
            "else echo ''; fi"
        )
        _stdin, stdout, _stderr = client.exec_command(command)
        output = stdout.read().decode("utf-8")
        entries = []
        if output.strip():
            for line in output.strip().split("\n"):
                line = line.strip()
                if line:
                    entries.append(line)
        return entries

    def get_cpu_for_domain(self, client, domain):
        """Get CPU usage for a domain.

        Note: Does not validate - used for data loading from server."""

        safe_domain = sanitize_path_component(domain)
        cmd = (
            f"ps aux | grep -i '{safe_domain}' | grep -v grep "
            f"| awk '{{sum+=$3}} END {{printf \"%.1f\", sum}}'"
        )
        _, out, _ = client.exec_command(cmd, timeout=8)
        val = out.read().decode().strip()
        return float(val) if val else 0

    def get_memory_for_domain(self, client, domain):
        """Get memory usage for a domain.

        Note: Does not validate - used for data loading from server."""

        safe_domain = sanitize_path_component(domain)
        cmd = (
            f"ps aux | grep -i '{safe_domain}' | grep -v grep "
            f"| awk '{{sum+=$4}} END {{printf \"%.1f\", sum}}'"
        )
        _, out, _ = client.exec_command(cmd, timeout=8)
        val = out.read().decode().strip()
        return float(val) if val else 0

    def get_db_speed(self, client):
        cmd = (
            "if command -v mysqladmin >/dev/null 2>&1; then "
            "  start=$(date +%s%N); "
            "  mysqladmin ping >/dev/null 2>&1; "
            "  end=$(date +%s%N); "
            "  echo $(( (end - start) / 1000000 )); "
            "else echo 0; fi"
        )
        _, out, _ = client.exec_command(cmd, timeout=8)
        val = out.read().decode().strip()
        return float(val) if val else 0


    def get_server_cpu(self, client):
        """Overall CPU usage percentage."""
        cmd = (
            "top -bn1 | grep '^%Cpu\\|^Cpu' | "
            "head -1 | awk '{for(i=1;i<=NF;i++) if($i ~ /id/) print 100 - $(i-1)}'"
        )
        _, out, _ = client.exec_command(cmd, timeout=8)
        val = out.read().decode().strip()
        try:
            return float(val)
        except (ValueError, TypeError):
            return 0.0

    def get_server_memory(self, client):
        """Overall memory usage percentage."""
        cmd = "free | awk '/^Mem:/ {printf \"%.1f\", ($3/$2)*100}'"
        _, out, _ = client.exec_command(cmd, timeout=8)
        val = out.read().decode().strip()
        try:
            return float(val)
        except (ValueError, TypeError):
            return 0.0

    def get_server_disk(self, client):
        """Root partition disk usage percentage."""
        cmd = "df / | tail -1 | awk '{print $5}' | tr -d '%'"
        _, out, _ = client.exec_command(cmd, timeout=8)
        val = out.read().decode().strip()
        try:
            return float(val)
        except (ValueError, TypeError):
            return 0.0

    def count_git_repos(self, client):
        """Count Git repositories under /var/www."""
        cmd = "find /var/www -maxdepth 3 -name '.git' -type d 2>/dev/null | wc -l"
        _, out, _ = client.exec_command(cmd, timeout=10)
        val = out.read().decode().strip()
        try:
            return int(val)
        except (ValueError, TypeError):
            return 0

    def get_server_load_avg(self, client):
        """Return 1-min, 5-min, 15-min load averages as a tuple of floats."""
        cmd = "cat /proc/loadavg | awk '{print $1, $2, $3}'"
        _, out, _ = client.exec_command(cmd, timeout=8)
        val = out.read().decode().strip()
        try:
            parts = val.split()
            return float(parts[0]), float(parts[1]), float(parts[2])
        except (ValueError, TypeError, IndexError):
            return 0.0, 0.0, 0.0

    def get_active_connections(self, client):
        """Return the number of established TCP connections."""
        cmd = "ss -tun state established 2>/dev/null | tail -n +2 | wc -l"
        _, out, _ = client.exec_command(cmd, timeout=8)
        val = out.read().decode().strip()
        try:
            return int(val)
        except (ValueError, TypeError):
            return 0

    def get_process_count(self, client):
        """Return the total number of running processes."""
        cmd = "ps aux --no-heading 2>/dev/null | wc -l"
        _, out, _ = client.exec_command(cmd, timeout=8)
        val = out.read().decode().strip()
        try:
            return int(val)
        except (ValueError, TypeError):
            return 0

    def get_ssl_expiring_count(self, client, threshold_days=30):
        """Count subdomains whose SSL certificate expires within *threshold_days*.

        Checks every Apache vhost ServerName using openssl.
        """
        cmd = (
            "for conf in /etc/apache2/sites-available/*.conf; do "
            '[ -f "$conf" ] || continue; '
            "srv=$(grep -i '^[[:space:]]*ServerName' \"$conf\" | head -n1 | awk '{print $2}'); "
            '[ -z "$srv" ] && continue; '
            f"expiry=$(echo | timeout 3 openssl s_client -servername \"$srv\" -connect \"$srv:443\" 2>/dev/null "
            "| openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2); "
            '[ -z "$expiry" ] && continue; '
            "exp_epoch=$(date -d \"$expiry\" +%s 2>/dev/null); "
            "now_epoch=$(date +%s); "
            f"days_left=$(( (exp_epoch - now_epoch) / 86400 )); "
            f'[ "$days_left" -le {int(threshold_days)} ] && echo "$srv"; '
            "done 2>/dev/null | wc -l"
        )
        _, out, _ = client.exec_command(cmd, timeout=60)
        val = out.read().decode().strip()
        try:
            return int(val)
        except (ValueError, TypeError):
            return 0

    def get_subdomains_down_count(self, client):
        """Count subdomains returning HTTP 5xx or timing out."""
        cmd = (
            "down=0; "
            "for conf in /etc/apache2/sites-available/*.conf; do "
            '[ -f "$conf" ] || continue; '
            "srv=$(grep -i '^[[:space:]]*ServerName' \"$conf\" | head -n1 | awk '{print $2}'); "
            '[ -z "$srv" ] && continue; '
            "code=$(curl -o /dev/null -s -w '%{http_code}' --max-time 3 \"http://$srv\" 2>/dev/null); "
            '[ "$code" -ge 500 ] 2>/dev/null && down=$((down+1)); '
            '[ "$code" = "000" ] && down=$((down+1)); '
            "done; echo $down"
        )
        _, out, _ = client.exec_command(cmd, timeout=120)
        val = out.read().decode().strip()
        try:
            return int(val)
        except (ValueError, TypeError):
            return 0

    def get_all_ssl_certs(self, client, domains=None):
        """Fetch SSL certificate info for a specific list of domains.

        Returns a list of dicts:
            {domain, issuer, not_before, not_after, days_remaining, status}
        status: 'Valid' | 'Expiring Soon' | 'Expired' | 'No SSL'
        """
        import re
        from datetime import datetime, timezone

        if not domains:
            return []

        domain_args = " ".join(domains)

        cmd = (
            f"for domain in {domain_args}; do "
            'echo "DOMAIN:$domain"; '
            'cert=""; '
            'if [ -f "/etc/letsencrypt/live/$domain/cert.pem" ]; then '
            'cert="/etc/letsencrypt/live/$domain/cert.pem"; '
            'elif [ -f "/etc/letsencrypt/live/$domain/fullchain.pem" ]; then '
            'cert="/etc/letsencrypt/live/$domain/fullchain.pem"; '
            'fi; '
            'if [ -z "$cert" ]; then '
            'for c in /etc/apache2/sites-enabled/$domain.conf '
            '/etc/apache2/sites-enabled/$domain-le-ssl.conf '
            '/etc/apache2/sites-available/$domain.conf; do '
            '[ -f "$c" ] || continue; '
            "cert=$(grep -i 'SSLCertificateFile' \"$c\" | head -1 | awk '{print $2}'); "
            '[ -n "$cert" ] && break; '
            'done; fi; '
            'if [ -n "$cert" ] && [ -f "$cert" ]; then '
            'echo "ISSUER:$(timeout 5 openssl x509 -noout -issuer -in $cert 2>/dev/null)"; '
            'echo "NOT_BEFORE:$(timeout 5 openssl x509 -noout -startdate -in $cert 2>/dev/null)"; '
            'echo "NOT_AFTER:$(timeout 5 openssl x509 -noout -enddate -in $cert 2>/dev/null)"; '
            "else echo 'ISSUER:No SSL'; echo 'NOT_BEFORE:'; echo 'NOT_AFTER:'; fi; "
            "echo '---END---'; done"
        )
        _, out, _ = client.exec_command(cmd, timeout=90)
        raw = out.read().decode(errors="replace")

        results = []
        current = {}
        now_utc = datetime.now(timezone.utc)

        def _flush(c):
            if not c.get("domain"):
                return
            issuer_raw = c.get("issuer", "")
            m = re.search(r"CN\s*=\s*([^,/\n]+)", issuer_raw)
            issuer = m.group(1).strip() if m else (issuer_raw.strip() or "Unknown")

            if issuer_raw.strip() == "No SSL":
                c["issuer"] = "—"
                c["not_before"] = "—"
                c["not_after"] = "—"
                c["days_remaining"] = "—"
                c["status"] = "No SSL"
                results.append(c)
                return

            c["issuer"] = issuer

            def _parse_date(raw_val):
                val = re.sub(r"not(?:Before|After)=", "", raw_val).strip()
                for fmt in ("%b %d %H:%M:%S %Y %Z", "%b  %d %H:%M:%S %Y %Z"):
                    try:
                        return datetime.strptime(val, fmt).replace(tzinfo=timezone.utc)
                    except ValueError:
                        continue
                return None

            nb = _parse_date(c.get("not_before_raw", ""))
            na = _parse_date(c.get("not_after_raw", ""))
            c["not_before"] = nb.strftime("%Y-%m-%d") if nb else "—"
            c["not_after"]  = na.strftime("%Y-%m-%d") if na else "—"

            if na:
                days = (na - now_utc).days
                c["days_remaining"] = days
                if days < 0:
                    c["status"] = "Expired"
                elif days <= 30:
                    c["status"] = "Expiring Soon"
                else:
                    c["status"] = "Valid"
            else:
                c["days_remaining"] = "—"
                c["status"] = "Unknown"

            results.append(c)

        for line in raw.splitlines():
            line = line.strip()
            if line == "---END---":
                _flush(current)
                current = {}
            elif line.startswith("DOMAIN:"):
                current["domain"] = line[7:].strip()
            elif line.startswith("ISSUER:"):
                current["issuer"] = line[7:].strip()
            elif line.startswith("NOT_BEFORE:"):
                current["not_before_raw"] = line[11:].strip()
            elif line.startswith("NOT_AFTER:"):
                current["not_after_raw"] = line[10:].strip()

        return results

    def delete_subdomain(self, client, domain):
        """Delete a subdomain's web root folder and Apache vhost config.

        Steps:
        1. Remove /var/www/<domain> directory
        2. Disable and remove the Apache vhost config
        3. Remove entry from /root/custom_dns.txt if present
        4. Reload Apache

        Note: Validates input as it's user-triggered action."""

        is_valid, error = validate_domain_name(domain)
        if not is_valid:
            raise ValueError(f"Invalid domain: {error}")

        safe_domain = sanitize_path_component(domain)

        errors = []


        cmd_rm_www = f"rm -rf /var/www/{safe_domain}"
        _, _, stderr = client.exec_command(cmd_rm_www)
        err = stderr.read().decode().strip()
        if err:
            errors.append(f"www: {err}")


        cmd_disable = f"a2dissite {safe_domain}.conf 2>/dev/null || true"
        _, _, stderr = client.exec_command(cmd_disable)
        err = stderr.read().decode().strip()
        if err and "does not exist" not in err.lower():
            errors.append(f"a2dissite: {err}")


        cmd_rm_conf = f"rm -f /etc/apache2/sites-available/{safe_domain}.conf"
        _, _, stderr = client.exec_command(cmd_rm_conf)
        err = stderr.read().decode().strip()
        if err:
            errors.append(f"conf: {err}")


        safe_domain_sed = sanitize_for_sed(domain)
        cmd_rm_dns = f"sed -i '/{safe_domain_sed}/d' /root/custom_dns.txt 2>/dev/null || true"
        _, _, stderr = client.exec_command(cmd_rm_dns)
        err = stderr.read().decode().strip()
        if err:
            errors.append(f"dns: {err}")


        cmd_reload = "systemctl reload apache2 2>/dev/null || service apache2 reload 2>/dev/null || true"
        _, _, stderr = client.exec_command(cmd_reload)
        err = stderr.read().decode().strip()
        if err:
            errors.append(f"reload: {err}")

        if errors:
            raise RuntimeError("; ".join(errors))

