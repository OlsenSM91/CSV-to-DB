from fastapi import FastAPI, Request, Form, UploadFile, File, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, StreamingResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, select, or_, and_, func
from sqlalchemy.orm import sessionmaker, joinedload
from starlette.status import HTTP_303_SEE_OTHER
import os
import io
import csv
import json
from datetime import datetime
from models import Base, Client, Workstation
from utils import import_csv_to_db, export_workstations
from connectwise_api import find_company_by_name, create_project_ticket, check_company_workstations_ready

DB_PATH = 'sqlite:///./database.db'
engine = create_engine(DB_PATH, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(bind=engine)

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


class ConnectionManager:
    def __init__(self):
        self.active_connections = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)

    async def broadcast(self, message: dict):
        data = json.dumps(message)
        disconnected = []
        for connection in list(self.active_connections):
            try:
                await connection.send_text(data)
            except Exception:
                disconnected.append(connection)
        for conn in disconnected:
            self.disconnect(conn)


manager = ConnectionManager()

TECHNICIANS = ["Brian", "Ed", "Steven", "Roy", "Jessica"]
STATUS_LIST = [
    "- Select Status -", "Assigned", "Ready to Upgrade", "Scheduled", "In Progress",
    "Waiting on Product", "Must Quote", "Awaiting Client Response", "Needs RAM Upgrade", "Completed"
]

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def compute_stats(db):
    total = db.query(Workstation).count()
    completed = db.query(Workstation).filter(Workstation.status == "Completed").count()
    in_progress = db.query(Workstation).filter(Workstation.status == "In Progress").count()
    ready = db.query(Workstation).filter(Workstation.status == "Ready to Upgrade").count()
    not_started = db.query(Workstation).filter(
        Workstation.status.in_(["- Select Status -", "Assigned", "Pending Upgrade"])
    ).count()
    completed_and_updated = db.query(Workstation).filter(
        Workstation.status == "Completed",
        Workstation.updated_in_automate == True,
    ).count()
    return {
        "total": total,
        "completed": completed,
        "in_progress": in_progress,
        "not_started": not_started,
        "ready_to_upgrade": ready,
        "completed_and_updated": completed_and_updated,
    }

def build_dashboard_context(
    request: Request,
    db,
    client: str = "",
    ram: str = "",
    technician: str = "",
    status: str = "",
    search: str = "",
    automate: str = "",
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
    if automate:
        if automate == "updated":
            ws_query = ws_query.filter(Workstation.updated_in_automate == True)
        elif automate == "not-updated":
            ws_query = ws_query.filter(Workstation.updated_in_automate == False)
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

    clients = {}
    for ws in workstations:
        if ws.client:
            cid = ws.client.id
            cname = ws.client.name
        else:
            cid = None
            cname = "Unknown"
        if cid not in clients:
            clients[cid] = {"id": cid, "name": cname, "workstations": []}
        clients[cid]["workstations"].append(ws)

    for client_data in clients.values():
        client_data["workstations"].sort(key=lambda w: w.computer_name.lower())
        ws_dicts = [
            {
                "computer_name": ws.computer_name,
                "processor_name": ws.processor_name,
                "ram_gb": ws.ram_gb,
                "diskspace_remaining_gb": ws.diskspace_remaining_gb,
                "status": ws.status,
                "technician": ws.technician,
                "notes": ws.notes
            }
            for ws in client_data["workstations"]
        ]
        client_data["ready_for_ticket"] = check_company_workstations_ready(ws_dicts)

    clients_list = list(clients.values())
    clients_list.sort(key=lambda c: c["name"])

    stats = compute_stats(db)

    all_clients = [c.name for c in db.query(Client).order_by(Client.name)]
    all_ram = sorted(set(ws.ram_gb for ws in db.query(Workstation) if ws.ram_gb))
    all_clients_objs = db.query(Client).order_by(Client.name).all()

    return {
        "request": request,
        "clients": clients_list,
        "technicians": TECHNICIANS,
        "statuses": STATUS_LIST,
        "all_clients": all_clients,
        "all_ram": all_ram,
        "all_clients_objs": all_clients_objs,
        "stats": stats,
    }

@app.get("/", response_class=HTMLResponse)
def dashboard(
    request: Request,
    client: str = "",
    ram: str = "",
    technician: str = "",
    status: str = "",
    search: str = "",
    automate: str = "",
    db=Depends(get_db)
):
    context = build_dashboard_context(
        request,
        db,
        client=client,
        ram=ram,
        technician=technician,
        status=status,
        search=search,
        automate=automate,
    )
    return templates.TemplateResponse("dashboard.html", context)


@app.get("/fragment", response_class=HTMLResponse)
def dashboard_fragment(
    request: Request,
    client: str = "",
    ram: str = "",
    technician: str = "",
    status: str = "",
    search: str = "",
    automate: str = "",
    db=Depends(get_db),
):
    context = build_dashboard_context(
        request,
        db,
        client=client,
        ram=ram,
        technician=technician,
        status=status,
        search=search,
        automate=automate,
    )
    return templates.TemplateResponse("dashboard_fragment.html", context)

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
        updated_in_automate=False
    )
    db.add(ws)
    db.commit()
    await manager.broadcast({"action": "refresh"})
    if request.headers.get("x-requested-with") == "XMLHttpRequest" or "application/json" in request.headers.get("accept", ""):
        return JSONResponse({"success": True})
    return RedirectResponse("/", status_code=HTTP_303_SEE_OTHER)

@app.post("/workstations/{ws_id}/edit")
async def edit_workstation(
    request: Request,
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
    
    # Track if status changed to completed
    if ws.status != "Completed" and status == "Completed":
        ws.completed_at = datetime.utcnow()
    elif ws.status == "Completed" and status != "Completed":
        # If changing from completed to something else, reset the automate checkbox
        ws.updated_in_automate = False
        ws.completed_at = None
    
    ws.computer_name = computer_name
    ws.processor_name = processor_name
    ws.ram_gb = ram_gb
    ws.diskspace_remaining_gb = diskspace_remaining_gb
    ws.status = status
    ws.technician = technician
    ws.notes = notes
    db.commit()
    await manager.broadcast({"action": "refresh"})
    if request.headers.get("x-requested-with") == "XMLHttpRequest" or "application/json" in request.headers.get("accept", ""):
        return JSONResponse({"success": True})
    return RedirectResponse("/", status_code=HTTP_303_SEE_OTHER)

@app.post("/workstations/{ws_id}/delete")
async def delete_workstation(
    request: Request,
    ws_id: int,
    db=Depends(get_db)
):
    ws = db.query(Workstation).filter_by(id=ws_id).first()
    if ws:
        db.delete(ws)
        db.commit()
        await manager.broadcast({"action": "refresh"})
    if request.headers.get("x-requested-with") == "XMLHttpRequest" or "application/json" in request.headers.get("accept", ""):
        return JSONResponse({"success": True})
    return RedirectResponse("/", status_code=HTTP_303_SEE_OTHER)

@app.get("/export")
def export_filtered(
    client: str = "",
    ram: str = "",
    technician: str = "",
    status: str = "",
    search: str = "",
    automate: str = "",
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
    if automate:
        if automate == "updated":
            ws_query = ws_query.filter(Workstation.updated_in_automate == True)
        elif automate == "not-updated":
            ws_query = ws_query.filter(Workstation.updated_in_automate == False)
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
        "Notes",
        "Updated in Automate",
        "Completed Date"
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
            ws.notes,
            "Yes" if ws.updated_in_automate else "No",
            ws.completed_at.strftime("%Y-%m-%d %H:%M") if ws.completed_at else ""
        ])
    
    output.seek(0)
    return StreamingResponse(
        output, 
        media_type="text/csv", 
        headers={"Content-Disposition": "attachment; filename=workstations.csv"}
    )

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
    if field not in ("status", "technician", "notes", "updated_in_automate"):
        return JSONResponse({"ok": False, "error": "Bad field"})
    
    # Handle status changes
    if field == "status":
        if ws.status != "Completed" and value == "Completed":
            ws.completed_at = datetime.utcnow()
        elif ws.status == "Completed" and value != "Completed":
            ws.updated_in_automate = False
            ws.completed_at = None
    
    # Handle automate checkbox
    if field == "updated_in_automate":
        ws.updated_in_automate = value.lower() in ['true', '1', 'yes']
    else:
        setattr(ws, field, value)

    db.commit()
    stats = compute_stats(db)
    await manager.broadcast({
        "action": "field_update",
        "id": ws.id,
        "field": field,
        "value": getattr(ws, field),
        "stats": stats,
    })
    return JSONResponse({"ok": True})

@app.post("/import")
async def import_csv(
    request: Request,
    file: UploadFile = File(...),
    db=Depends(get_db)
):
    # Save uploaded file temporarily
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
    
    try:
        import_csv_to_db(temp_path, db)
        os.remove(temp_path)
        await manager.broadcast({"action": "refresh"})
        if request.headers.get("x-requested-with") == "XMLHttpRequest" or "application/json" in request.headers.get("accept", ""):
            return JSONResponse({"success": True})
        return RedirectResponse("/", status_code=HTTP_303_SEE_OTHER)
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/create-project-ticket/{client_id}")
async def create_project_ticket_endpoint(
    client_id: int,
    db=Depends(get_db)
):
    """Create a ConnectWise project ticket for Windows 11 upgrades."""
    # Get the client
    client = db.query(Client).filter_by(id=client_id).first()
    if not client:
        return JSONResponse({"success": False, "error": "Client not found"}, status_code=404)
    
    # Get all workstations for this client
    workstations = db.query(Workstation).filter_by(client_id=client_id).all()
    
    # Convert to dict format for the API
    ws_data = [
        {
            "computer_name": ws.computer_name,
            "processor_name": ws.processor_name,
            "ram_gb": ws.ram_gb,
            "diskspace_remaining_gb": ws.diskspace_remaining_gb,
            "status": ws.status,
            "technician": ws.technician,
            "notes": ws.notes
        }
        for ws in workstations
    ]
    
    # Check if ready (all have status and technician)
    if not check_company_workstations_ready(ws_data):
        return JSONResponse({
            "success": False, 
            "error": "All workstations must have a status and technician assigned"
        }, status_code=400)
    
    # Find the company in ConnectWise
    cw_company = await find_company_by_name(client.name)
    if not cw_company:
        return JSONResponse({
            "success": False,
            "error": f"Could not find company '{client.name}' in ConnectWise"
        }, status_code=404)
    
    # Create the ticket
    success, ticket_id, message = await create_project_ticket(
        company_id=cw_company['id'],
        workstations=ws_data
    )
    
    if success:
        return JSONResponse({
            "success": True,
            "ticket_id": ticket_id,
            "message": message,
            "cw_company_name": cw_company['name']
        })
    else:
        return JSONResponse({
            "success": False,
            "error": message
        }, status_code=500)

@app.get("/check-ticket-readiness/{client_id}")
async def check_ticket_readiness(
    client_id: int,
    db=Depends(get_db)
):
    """Check if a client is ready for project ticket creation."""
    workstations = db.query(Workstation).filter_by(client_id=client_id).all()
    
    ws_data = [
        {
            "status": ws.status,
            "technician": ws.technician
        }
        for ws in workstations
    ]
    
    ready = check_company_workstations_ready(ws_data)
    return JSONResponse({"ready": ready})


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
