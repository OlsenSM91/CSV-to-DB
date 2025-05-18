import pandas as pd
from sqlalchemy.orm import Session
from models import Client, Workstation

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
        ws = Workstation(
            client=client,
            computer_name=str(row.get("Computer Name", "")),
            ram_gb=str(row.get("RAM_GB", "")),
            processor_name=str(row.get("Processor Name", "")),
            diskspace_remaining_gb=str(row.get("DiskSpaceRemaining_GB", "")),
            status="Pending Upgrade",
            technician="",
            notes=""
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
            "Notes": ws.notes
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
