"""
Vultr DNS API helpers — fetch and register subdomain records.
"""
import os

from models.config import HAS_REQUESTS, VULTR_API_KEY, VULTR_BASE_URL, VULTR_TARGET_DOMAIN
from models.logger import module_logger

if HAS_REQUESTS:
    import requests


logger = module_logger(__name__)


def _get_vultr_settings(domain=None):
    """Read Vultr settings from current process env with config fallbacks."""
    api_key = os.getenv("VULTR_API_KEY", VULTR_API_KEY or "").strip()
    base_url = os.getenv("VULTR_BASE_URL", VULTR_BASE_URL or "https://api.vultr.com/v2").strip()
    target_domain = (domain or os.getenv("VULTR_TARGET_DOMAIN", VULTR_TARGET_DOMAIN or "veryapp.info")).strip()
    return api_key, base_url, target_domain


def fetch_vultr_subdomains(domain=None):
    """
    Fetch all subdomains for a specific domain from Vultr DNS API.
    Returns a list of dicts: [{"subdomain": full_name, "type": record_type, "data": data}]
    """
    if not HAS_REQUESTS:
        logger.error("requests library not available")
        print("Error: requests library not available")
        return []

    api_key, base_url, target_domain = _get_vultr_settings(domain)

    # Check if API key is configured
    if not api_key or api_key == "your_vultr_api_key_here":
        logger.warning("VULTR_API_KEY not configured - skipping Vultr DNS fetch")
        print("Warning: VULTR_API_KEY not configured - skipping Vultr DNS fetch")
        return []

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    subdomains = []

    try:
        logger.info(f"Fetching Vultr DNS records for domain: {target_domain}")
        records_response = requests.get(
            f"{base_url}/domains/{target_domain}/records",
            headers=headers,
            timeout=30,
        )
        
        # Log HTTP status for debugging
        if records_response.status_code != 200:
            logger.error(f"Vultr API returned HTTP {records_response.status_code}: {records_response.text}")
            print(f"Error: Vultr API returned HTTP {records_response.status_code}")
            return []
        
        records_data = records_response.json()

        if "error" in records_data:
            logger.error(f"Vultr API error response: {records_data}")
            print(f"Error fetching records: {records_data}")
            return []

        records = records_data.get("records", [])

        for record in records:
            record_type = record.get("type")
            name = record.get("name")
            data = record.get("data")

            if name == "@" or name == "":
                full_name = target_domain
            else:
                full_name = f"{name}.{target_domain}"

            if record_type in ["A", "AAAA", "CNAME"]:
                subdomains.append(
                    {
                        "subdomain": full_name,
                        "type": record_type,
                        "data": data,
                        "domain": target_domain,
                    }
                )

        print(f"Fetched {len(subdomains)} subdomains from Vultr for domain: {target_domain}")

    except requests.exceptions.RequestException as e:
        print(f"Error connecting to Vultr API: {e}")
    except Exception as e:
        print(f"Error fetching Vultr subdomains: {e}")

    return subdomains


def register_vultr_subdomain(subdomain, ip, domain=None):
    """
    Register a new A record on Vultr DNS for the given subdomain.
    Returns (success: bool, message: str).
    """
    if not HAS_REQUESTS:
        return False, "requests library not available"

    api_key, base_url, target_domain = _get_vultr_settings(domain)

    if subdomain.lower().endswith(f".{target_domain.lower()}"):
        name = subdomain[: -(len(target_domain) + 1)]
    elif subdomain.lower() == target_domain.lower():
        name = ""
    else:
        name = subdomain

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {"name": name, "type": "A", "data": ip, "ttl": 300}

    try:
        resp = requests.post(
            f"{base_url}/domains/{target_domain}/records",
            headers=headers,
            json=payload,
            timeout=30,
        )
        if resp.status_code in (200, 201):
            return True, f"Vultr DNS record created: {subdomain} -> {ip}"
        else:
            body = resp.text
            return False, f"Vultr API error ({resp.status_code}): {body}"
    except requests.exceptions.RequestException as e:
        return False, f"Vultr API request failed: {e}"
    except Exception as e:
        return False, f"Unexpected error registering on Vultr: {e}"


def delete_vultr_subdomain(subdomain, domain=None):
    """
    Delete all DNS records for the given subdomain from Vultr.
    Finds matching record IDs first, then issues DELETE for each.
    Returns (success: bool, message: str).
    """
    if not HAS_REQUESTS:
        return False, "requests library not available"

    api_key, base_url, target_domain = _get_vultr_settings(domain)


    if subdomain.lower().endswith(f".{target_domain.lower()}"):
        name = subdomain[: -(len(target_domain) + 1)]
    elif subdomain.lower() == target_domain.lower():
        name = ""
    else:
        name = subdomain

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:

        resp = requests.get(
            f"{base_url}/domains/{target_domain}/records",
            headers=headers,
            timeout=30,
        )
        if resp.status_code != 200:
            return False, f"Failed to fetch DNS records ({resp.status_code}): {resp.text}"

        records = resp.json().get("records", [])


        matching = [r for r in records if r.get("name", "") == name]
        if not matching:
            return True, f"No Vultr DNS records found for '{subdomain}' — nothing to delete."

        deleted = 0
        errors = []
        for record in matching:
            record_id = record.get("id")
            del_resp = requests.delete(
                f"{base_url}/domains/{target_domain}/records/{record_id}",
                headers=headers,
                timeout=30,
            )
            if del_resp.status_code in (200, 204):
                deleted += 1
            else:
                errors.append(f"Record {record_id} ({record.get('type')}): {del_resp.status_code}")

        if errors:
            return False, f"Deleted {deleted} record(s), but failed on: {'; '.join(errors)}"

        return True, f"Deleted {deleted} Vultr DNS record(s) for '{subdomain}'."

    except requests.exceptions.RequestException as e:
        return False, f"Vultr API request failed: {e}"
    except Exception as e:
        return False, f"Unexpected error deleting Vultr record: {e}"
