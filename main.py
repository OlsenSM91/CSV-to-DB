from fastapi import FastAPI, Request, Form, UploadFile, File, Depends, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, select, or_, and_, func
from sqlalchemy.orm import sessionmaker, joinedload
from starlette.status import HTTP_303_SEE_OTHER
import os
import io
import csv
from models import Base, Client, Workstation
from utils import import_csv_to_db, export_workstations

DB_PATH = 'sqlite:///./database.db'
engine = create_engine(DB_PATH, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(bind=engine)

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

TECHNICIANS = ["Brian", "Ed", "Steven", "Roy", "Jessica"]
STATUS_LIST = [
    "- Select Status -", "Under Review", "Assigned", "Ready to Upgrade", "Scheduled", "In Progress",
    "Waiting on Product", "Must Quote", "Awaiting Client Response", "Needs RAM Upgrade", "Completed"
]

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/", response_class=HTMLResponse)
def dashboard(
    request: Request,
    client: str = "",
    ram: str = "",
    technician: str = "",
    status: str = "",
    search: str = "",
    db=Depends(get_db)
):
    ws_query = db.query(Workstation).options(joinedload(Workstation.client))
    if client:
        ws_query = ws_query.join(Client).filter(Client.name == client)
    if ram:
        ws_query = ws_query.filter(Workstation.ram_gb == ram)
    if technician:
        ws_query = ws_query.filter(Workstation.technician == technician)
    if status:
        ws_query = ws_query.filter(Workstation.status == status)
    if search:
        like = f"%{search}%"
        ws_query = ws_query.filter(
            or_(
                Workstation.computer_name.ilike(like),
                Workstation.processor_name.ilike(like),
                Workstation.diskspace_remaining_gb.ilike(like),
                Workstation.notes.ilike(like),
                Client.name.ilike(like)
            )
        )
    workstations = ws_query.all()

    # --- NEW GROUPING LOGIC ---
    clients = {}
    for ws in workstations:
        # Key on client id, not just name
        if ws.client:
            cid = ws.client.id
            cname = ws.client.name
        else:
            cid = None
            cname = "Unknown"
        if cid not in clients:
            clients[cid] = {"id": cid, "name": cname, "workstations": []}
        clients[cid]["workstations"].append(ws)
    clients_list = list(clients.values())
    clients_list.sort(key=lambda c: c["name"])

    all_clients = [c.name for c in db.query(Client).order_by(Client.name)]
    all_ram = sorted(set(ws.ram_gb for ws in db.query(Workstation) if ws.ram_gb))
    all_clients_objs = db.query(Client).order_by(Client.name).all()
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "clients": clients_list,
        "technicians": TECHNICIANS,
        "statuses": STATUS_LIST,
        "all_clients": all_clients,
        "all_ram": all_ram,
        "all_clients_objs": all_clients_objs,
    })

@app.post("/workstations/add")
async def add_workstation(
    request: Request,
    client_id: int = Form(...),
    computer_name: str = Form(...),
    processor_name: str = Form(...),
    ram_gb: str = Form(...),
    diskspace_remaining_gb: str = Form(...),
    status: str = Form(...),
    technician: str = Form(""),
    notes: str = Form(""),
    db=Depends(get_db)
):
    ws = Workstation(
        client_id=client_id,
        computer_name=computer_name,
        processor_name=processor_name,
        ram_gb=ram_gb,
        diskspace_remaining_gb=diskspace_remaining_gb,
        status=status,
        technician=technician,
        notes=notes,
    )
    db.add(ws)
    db.commit()
    return RedirectResponse("/", status_code=HTTP_303_SEE_OTHER)

@app.post("/workstations/{ws_id}/edit")
async def edit_workstation(
    ws_id: int,
    computer_name: str = Form(...),
    processor_name: str = Form(...),
    ram_gb: str = Form(...),
    diskspace_remaining_gb: str = Form(...),
    status: str = Form(...),
    technician: str = Form(""),
    notes: str = Form(""),
    db=Depends(get_db)
):
    ws = db.query(Workstation).filter_by(id=ws_id).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Workstation not found")
    ws.computer_name = computer_name
    ws.processor_name = processor_name
    ws.ram_gb = ram_gb
    ws.diskspace_remaining_gb = diskspace_remaining_gb
    ws.status = status
    ws.technician = technician
    ws.notes = notes
    db.commit()
    return RedirectResponse("/", status_code=HTTP_303_SEE_OTHER)

@app.post("/workstations/{ws_id}/delete")
async def delete_workstation(
    ws_id: int,
    db=Depends(get_db)
):
    ws = db.query(Workstation).filter_by(id=ws_id).first()
    if ws:
        db.delete(ws)
        db.commit()
    return RedirectResponse("/", status_code=HTTP_303_SEE_OTHER)

@app.get("/export")
def export_filtered(
    client: str = "",
    ram: str = "",
    technician: str = "",
    status: str = "",
    search: str = "",
    db=Depends(get_db)
):
    ws_query = db.query(Workstation).options(joinedload(Workstation.client))
    if client:
        ws_query = ws_query.join(Client).filter(Client.name.ilike(f"%{client.strip()}%"))
    if ram:
        ws_query = ws_query.filter(Workstation.ram_gb.ilike(f"%{ram.strip()}%"))
    if technician:
        ws_query = ws_query.filter(Workstation.technician.ilike(f"%{technician.strip()}%"))
    if status:
        ws_query = ws_query.filter(Workstation.status.ilike(f"%{status.strip()}%"))
    if search:
        like = f"%{search}%"
        ws_query = ws_query.filter(
            or_(
                Workstation.computer_name.ilike(like),
                Workstation.processor_name.ilike(like),
                Workstation.diskspace_remaining_gb.ilike(like),
                Workstation.notes.ilike(like),
                Client.name.ilike(like)
            )
        )
    workstations = ws_query.all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Client",
        "Computer Name",
        "Processor Name",
        "RAM (GB)",
        "Disk Space Remaining (GB)",
        "Status",
        "Technician",
        "Notes"
    ])
    for ws in workstations:
        writer.writerow([
            ws.client.name if ws.client else "",
            ws.computer_name,
            ws.processor_name,
            ws.ram_gb,
            ws.diskspace_remaining_gb,
            ws.status,
            ws.technician,
            ws.notes
        ])
    output.seek(0)
    return StreamingResponse(output, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=workstations.csv"})

@app.post("/update")
async def update_field(
    id: int = Form(...),
    field: str = Form(...),
    value: str = Form(...),
    db=Depends(get_db)
):
    ws = db.query(Workstation).filter_by(id=id).first()
    if not ws:
        return JSONResponse({"ok": False, "error": "Not found"})
    # Only allow specific fields to be updated
    if field not in ("status", "technician", "notes"):
        return JSONResponse({"ok": False, "error": "Bad field"})
    setattr(ws, field, value)
    db.commit()
    return JSONResponse({"ok": True})
