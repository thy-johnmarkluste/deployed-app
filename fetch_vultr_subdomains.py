"""
Fetch all registered subdomains from Vultr DNS API
"""
import os
import sys

import requests

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv:
    load_dotenv()

BASE_URL = "https://api.vultr.com/v2"
VULTR_API_KEY = os.getenv("VULTR_API_KEY", "").strip()

if not VULTR_API_KEY:
    print("Error: VULTR_API_KEY is not set.")
    print("Set it in your environment or local .env file before running this script.")
    print("Security note: the old exposed key should be revoked and rotated in Vultr immediately.")
    sys.exit(1)

headers = {
    "Authorization": f"Bearer {VULTR_API_KEY}",
    "Content-Type": "application/json"
}

# Get all domains
print("Fetching domains from Vultr...")
domains_response = requests.get(f"{BASE_URL}/domains", headers=headers)
domains_data = domains_response.json()

if "domains" not in domains_data:
    print(f"Error fetching domains: {domains_data}")
    exit(1)

domains = domains_data.get("domains", [])
print(f"\nFound {len(domains)} domain(s):\n")

all_subdomains = []

for domain_info in domains:
    domain = domain_info.get("domain")
    print(f"=" * 60)
    print(f"Domain: {domain}")
    print(f"=" * 60)
    
    # Get DNS records for this domain
    records_response = requests.get(f"{BASE_URL}/domains/{domain}/records", headers=headers)
    records_data = records_response.json()
    
    records = records_data.get("records", [])
    print(f"  Found {len(records)} DNS record(s):\n")
    
    for record in records:
        record_type = record.get("type")
        name = record.get("name")
        data = record.get("data")
        ttl = record.get("ttl")
        
        # Build full subdomain name
        if name == "@" or name == "":
            full_name = domain
        else:
            full_name = f"{name}.{domain}"
        
        print(f"  Type: {record_type:6} | Name: {full_name:40} | Data: {data}")
        
        # Collect A and CNAME records as subdomains
        if record_type in ["A", "AAAA", "CNAME"]:
            all_subdomains.append({
                "subdomain": full_name,
                "type": record_type,
                "data": data,
                "domain": domain
            })
    print()

print(f"\n{'=' * 60}")
print(f"SUMMARY: All Subdomains (A, AAAA, CNAME records)")
print(f"{'=' * 60}")
for idx, sub in enumerate(all_subdomains, 1):
    print(f"{idx:3}. {sub['subdomain']:40} -> {sub['data']} ({sub['type']})")

print(f"\nTotal: {len(all_subdomains)} subdomain(s)")
