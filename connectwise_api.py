import os
import httpx
import base64
from dotenv import load_dotenv
from typing import Optional, Dict, List, Tuple
import asyncio
from fuzzywuzzy import fuzz
from datetime import datetime

load_dotenv()

# Load env
BASE_URL = os.getenv("CW_BASE_URL")
CLIENT_ID = os.getenv("CW_CLIENT_ID")
COMPANY_ID = os.getenv("CW_COMPANY_ID")
PUBLIC_API_KEY = os.getenv("CW_PUBLIC_API_KEY")
PRIVATE_API_KEY = os.getenv("CW_PRIVATE_API_KEY")

# Build headers
auth_string = f"{COMPANY_ID}+{PUBLIC_API_KEY}:{PRIVATE_API_KEY}"
encoded_auth_string = base64.b64encode(auth_string.encode()).decode()

HEADERS = {
    "Authorization": f"Basic {encoded_auth_string}",
    "clientId": CLIENT_ID,
    "Content-Type": "application/json",
    "Accept": "application/json"
}

async def find_company_by_name(company_name: str) -> Optional[Dict]:
    """Find a company by name, with fuzzy matching fallback."""
    async with httpx.AsyncClient() as client:
        # First try exact match
        response = await client.get(
            f"{BASE_URL}/company/companies",
            headers=HEADERS,
            params={"conditions": f'name="{company_name}"'}
        )
        if response.status_code == 200:
            companies = response.json()
            if companies:
                return companies[0]
        # If no exact match, get all companies and do fuzzy matching
        response = await client.get(
            f"{BASE_URL}/company/companies",
            headers=HEADERS,
            params={"pageSize": 1000}  # Adjust if you have more companies
        )
        if response.status_code == 200:
            all_companies = response.json()
            best_match = None
            best_score = 0
            for company in all_companies:
                score = fuzz.ratio(company_name.lower(), company['name'].lower())
                if score > best_score and score > 80:  # 80% similarity threshold
                    best_score = score
                    best_match = company
            return best_match
    return None

async def find_member_by_name(technician_name: str) -> Optional[Dict]:
    """Find a ConnectWise member (resource) by name."""
    async with httpx.AsyncClient() as client:
        # Try to find member by identifier (usually firstname.lastname format)
        identifier = technician_name.lower().replace(" ", ".")
        response = await client.get(
            f"{BASE_URL}/system/members",
            headers=HEADERS,
            params={"conditions": f'identifier="{identifier}"'}
        )
        if response.status_code == 200:
            members = response.json()
            if members:
                return members[0]
        # If not found by identifier, search by name
        response = await client.get(
            f"{BASE_URL}/system/members",
            headers=HEADERS,
            params={"conditions": f'firstName="{technician_name}" OR lastName="{technician_name}"'}
        )
        if response.status_code == 200:
            members = response.json()
            if members:
                return members[0]
    return None

async def find_team_by_name(team_name: str) -> Optional[Dict]:
    """Find a ConnectWise team by name."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/service/teams",
            headers=HEADERS,
            params={"conditions": f'name="{team_name}"'}
        )
        if response.status_code == 200:
            teams = response.json()
            if teams:
                return teams[0]
    return None

async def assign_technician_to_ticket(ticket_id: int, member_id: int, member_name: str) -> bool:
    """Assign a technician to a ticket via schedule entry."""
    async with httpx.AsyncClient() as client:
        try:
            # Method 1: Try using the schedule API
            schedule_data = {
                "objectId": ticket_id,
                "type": {"identifier": "S"},  # S for Service ticket
                "member": {"id": member_id},
                "workRole": {"name": "Technician"},
                "dateStart": datetime.utcnow().isoformat() + "Z",
                "timeZone": {"name": "GMT-8/Pacific Time: US & Canada (UTC-07)"}
            }
            response = await client.post(
                f"{BASE_URL}/schedule/entries",
                headers=HEADERS,
                json=schedule_data,
                timeout=30.0
            )
            if response.status_code == 201:
                return True
            # Method 2: Try using the ticket update endpoint
            update_data = [{
                "op": "add",
                "path": "/resources",
                "value": member_name
            }]
            patch_response = await client.patch(
                f"{BASE_URL}/service/tickets/{ticket_id}",
                headers=HEADERS,
                json=update_data,
                timeout=30.0
            )
            return patch_response.status_code in [200, 201]
        except Exception as e:
            print(f"Error assigning {member_name} to ticket: {str(e)}")
            return False

async def create_project_ticket(
    company_id: int,
    workstations: List[Dict],
    board_name: str = "Professional Services"
) -> Tuple[bool, Optional[int], str]:
    """
    Create a project ticket for Windows 11 upgrades.
    Returns (success, ticket_id, error_message)
    """
    # Build the ticket description
    description_lines = [
        "Windows 11 Upgrade Project Details:",
        "",
        "Workstations to be upgraded:"
    ]
    # Group workstations by technician
    tech_workstations = {}
    for ws in workstations:
        tech = ws.get('technician', 'Unassigned')
        if tech not in tech_workstations:
            tech_workstations[tech] = []
        tech_workstations[tech].append(ws)
    # Add workstation details to description
    for tech, ws_list in tech_workstations.items():
        description_lines.append(f"\nAssigned to {tech}:")
        for ws in ws_list:
            description_lines.append(
                f"  • {ws['computer_name']} - {ws['processor_name']}, "
                f"{ws['ram_gb']}GB RAM, {ws['diskspace_remaining_gb']}GB free disk - "
                f"Status: {ws['status']}"
            )
            if ws.get('notes'):
                description_lines.append(f"    Notes: {ws['notes']}")
    description = "\n".join(description_lines)
    # Get unique technicians and build resources string
    unique_technicians = list(set(ws.get('technician') for ws in workstations if ws.get('technician')))
    resources_str = ", ".join(unique_technicians) if unique_technicians else ""
    # Create the ticket with team and resources
    ticket_data = {
        "company": {"id": company_id},
        "summary": "[PROJECT] Windows 11 Upgrades",
        "initialDescription": description,
        "board": {"name": board_name},
        "status": {"name": "New (portal)"},
        "type": {"name": "Installation"},
        "team": {"name": "Service Team"},
        "resources": resources_str  # Comma-separated list of technician names
    }
    print(f"[DEBUG] Creating ticket with data: {ticket_data}")
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/service/tickets",
            headers=HEADERS,
            json=ticket_data,
            timeout=30.0
        )
        print(f"[DEBUG] Ticket creation response: {response.status_code}")
        if response.status_code != 201:
            error_detail = ""
            try:
                error_json = response.json()
                error_detail = error_json.get("message", response.text)
                if "errors" in error_json:
                    for err in error_json.get("errors", []):
                        error_detail += f"\n{err.get('message', '')}"
            except Exception as e:
                error_detail = f"Error decoding response: {e}\n{response.text}"
            print(f"[ERROR] Ticket creation failed: {error_detail}")
            return False, None, f"Failed to create ticket: {error_detail}"
        ticket = response.json()
        ticket_id = ticket['id']
        print(f"[DEBUG] Ticket created successfully with ID: {ticket_id}")
        # Assign technicians to the ticket
        for tech_name in unique_technicians:
            print(f"[DEBUG] Looking up technician: {tech_name}")
            member = await find_member_by_name(tech_name)
            if member:
                print(f"[DEBUG] Found member {tech_name} with ID: {member['id']}")
                success = await assign_technician_to_ticket(ticket_id, member['id'], tech_name)
                if not success:
                    print(f"Warning: Failed to assign {tech_name} to ticket {ticket_id}")
            else:
                print(f"Warning: Could not find member {tech_name} in ConnectWise")
        return True, ticket_id, "Ticket created successfully"

def check_company_workstations_ready(workstations: List[Dict]) -> bool:
    """Check if all workstations for a company have status and technician assigned."""
    if not workstations:
        return False
    for ws in workstations:
        # Check if status is not the default/empty status
        if not ws.get('status') or ws.get('status') == '- Select Status -':
            return False
        # Check if technician is assigned
        if not ws.get('technician'):
            return False
    return True
