#!/usr/bin/env python3
"""
Scrape Walk4Friendship fundraiser data from Rallybound.
Outputs fundraiser-data.csv for the dashboard.

Usage:
    python3 scrape.py              # scrape and write CSV
    python3 scrape.py --preview    # print results without writing

Source: https://www.walk4friendship.com (Rallybound/Neon Fundraise)
"""

import csv
import re
import json
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

SITE = "https://www.walk4friendship.com"
MEMBER_ENDPOINT = f"{SITE}/Member/MemberList"
TEAM_ENDPOINT = f"{SITE}/Team/TeamList"
OUTPUT_DIR = Path(__file__).parent
FUNDRAISER_CSV = OUTPUT_DIR / "fundraiser-data.csv"

HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded",
    "X-Requested-With": "XMLHttpRequest",
    "User-Agent": "Walk4Friendship-Dashboard/1.0",
}


def fetch_members():
    """Fetch all walkers/fundraisers from Rallybound MemberList API."""
    body = "splitFirstAndLast=true&containerId=widget-c458d5ce-e8ed-4557-a387-e50896f929f4"
    data = body.encode("utf-8")

    req = urllib.request.Request(MEMBER_ENDPOINT, data=data, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read().decode("utf-8"))

    if not result.get("success"):
        print("Error: API returned success=false")
        sys.exit(1)

    html = result["html"]
    rows = html.split("tableRow ajaxTableRow")
    members = []

    for row in rows[1:]:  # skip first split (before first row)
        fn = re.search(r'tableColSortFirstName[^>]*><a[^>]*>([^<]+)</a>', row)
        ln = re.search(r'tableColSortLastName[^>]*><a[^>]*>([^<]+)</a>', row)
        amt = re.search(r'data-sort="([\d.]+)"', row)
        slug = re.search(r'data-href="/([^"]+)"', row)

        if fn and ln and amt:
            name = f"{fn.group(1)} {ln.group(1)}".strip()
            amount = float(amt.group(1))
            page_url = f"{SITE}/{slug.group(1)}" if slug else ""
            members.append({
                "Fundraiser Name": name,
                "Amount Raised": amount,
                "Page URL": page_url,
            })

    return members


def fetch_teams():
    """Fetch all teams from Rallybound TeamList API."""
    body = "containerId=widget-b9f0d7fa-a00d-45dd-8038-7477da79117f"
    data = body.encode("utf-8")

    req = urllib.request.Request(TEAM_ENDPOINT, data=data, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read().decode("utf-8"))

    if not result.get("success"):
        return []

    html = result["html"]
    rows = html.split("tableRow")
    teams = []

    for row in rows[1:]:
        if "ajaxTableRow" not in row and "data-href" not in row:
            continue
        name_match = re.search(r'tableColSortName[^>]*><a[^>]*>([^<]+)</a>', row)
        if not name_match:
            name_match = re.search(r'<a href="/[^"]*">([^<]+)</a>', row)
        amt = re.search(r'data-sort="([\d.]+)"', row)
        walkers = re.search(r'\((\d+)\s*walker', row)

        if name_match and amt:
            teams.append({
                "Team Name": name_match.group(1).strip(),
                "Amount Raised": float(amt.group(1)),
                "Walkers": int(walkers.group(1)) if walkers else 0,
            })

    return teams


def write_csv(members):
    """Write fundraiser data to CSV."""
    with open(FUNDRAISER_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["Fundraiser Name", "Amount Raised", "Page URL"])
        writer.writeheader()
        writer.writerows(members)


def main():
    preview = "--preview" in sys.argv

    print(f"Scraping {SITE}...")
    members = fetch_members()
    total = sum(m["Amount Raised"] for m in members)
    print(f"Found {len(members)} fundraisers, total raised: ${total:,.2f}")

    if preview:
        print("\nTop 20 fundraisers:")
        for m in sorted(members, key=lambda x: x["Amount Raised"], reverse=True)[:20]:
            print(f"  {m['Fundraiser Name']:30s}  ${m['Amount Raised']:>10,.2f}  {m['Page URL']}")
    else:
        write_csv(members)
        print(f"Wrote {FUNDRAISER_CSV}")

    # Also show teams
    teams = fetch_teams()
    if teams:
        print(f"\nFound {len(teams)} teams")
        if preview:
            for t in sorted(teams, key=lambda x: x["Amount Raised"], reverse=True)[:10]:
                print(f"  {t['Team Name']:30s}  ${t['Amount Raised']:>10,.2f}  ({t['Walkers']} walkers)")

    print(f"\nLast updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
