import pandas as pd
from sqlalchemy.orm import Session
from models import Client, Workstation
from datetime import datetime

def import_csv_to_db(csv_path, db: Session):
    # Clear existing data
    db.query(Workstation).delete()
    db.query(Client).delete()
    db.commit()

    df = pd.read_csv(csv_path)
    for _, row in df.iterrows():
        client_name = str(row.get("Client Name", "")).strip()
        if not client_name:
            continue
        client = db.query(Client).filter_by(name=client_name).first()
        if not client:
            client = Client(name=client_name)
            db.add(client)
            db.flush()
        
        # Check if this workstation was already completed
        status = str(row.get("Status", "Pending Upgrade"))
        completed_at = None
        if status == "Completed":
            # If there's a completed date in the CSV, use it
            if "Completed Date" in df.columns and pd.notna(row.get("Completed Date")):
                try:
                    completed_at = datetime.strptime(str(row.get("Completed Date")), "%Y-%m-%d %H:%M")
                except:
                    completed_at = datetime.utcnow()
            else:
                completed_at = datetime.utcnow()
        
        # Check for updated_in_automate field
        updated_in_automate = False
        if "Updated in Automate" in df.columns:
            automate_val = str(row.get("Updated in Automate", "")).lower()
            updated_in_automate = automate_val in ['yes', 'true', '1']
        
        ws = Workstation(
            client=client,
            computer_name=str(row.get("Computer Name", "")),
            ram_gb=str(row.get("RAM_GB", "")),
            processor_name=str(row.get("Processor Name", "")),
            diskspace_remaining_gb=str(row.get("DiskSpaceRemaining_GB", "")),
            status=status,
            technician=str(row.get("Technician", "")),
            notes=str(row.get("Notes", "")),
            updated_in_automate=updated_in_automate,
            completed_at=completed_at
        )
        db.add(ws)
    db.commit()

def export_workstations(workstations, export_type='csv'):
    import io
    import pandas as pd

    # Build a DataFrame from workstation ORM objects
    data = []
    for ws in workstations:
        data.append({
            "Client Name": ws.client.name if ws.client else "",
            "Computer Name": ws.computer_name,
            "RAM_GB": ws.ram_gb,
            "Processor Name": ws.processor_name,
            "DiskSpaceRemaining_GB": ws.diskspace_remaining_gb,
            "Status": ws.status,
            "Technician": ws.technician,
            "Notes": ws.notes,
            "Updated in Automate": "Yes" if ws.updated_in_automate else "No",
            "Completed Date": ws.completed_at.strftime("%Y-%m-%d %H:%M") if ws.completed_at else ""
        })
    df = pd.DataFrame(data)
    buf = io.BytesIO()
    if export_type == 'csv':
        df.to_csv(buf, index=False)
        buf.seek(0)
        return buf, 'text/csv', 'export.csv'
    elif export_type == 'xlsx':
        df.to_excel(buf, index=False)
        buf.seek(0)
        return buf, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'export.xlsx'
    return None, None, None

def check_company_workstations_ready(workstations):
    """
    Returns True only if every workstation:
      - Has a technician assigned (not None or blank)
      - Has a status that is not "- Select Status -" or "Assigned"
    """
    for ws in workstations:
        if not ws.get("technician") or ws["technician"].strip() == "":
            return False
        if ws.get("status") in ["- Select Status -", "Assigned", None, ""]:
            return False
    return True
