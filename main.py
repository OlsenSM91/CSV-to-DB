from fastapi import FastAPI, Request, Form, UploadFile, File, Depends
from fastapi.responses import HTMLResponse, StreamingResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, select, or_, and_, func
from sqlalchemy.orm import sessionmaker, joinedload
import os
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
    "- Select Status -", "Assigned", "Ready to Upgrade", "Scheduled", "In Progress",
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
    # Filtering logic
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
    # Group by client
    clients = {}
    for ws in workstations:
        cname = ws.client.name if ws.client else "Unknown"
        if cname not in clients:
            clients[cname] = []
        clients[cname].append(ws)
    clients_list = [{"name": cname, "workstations": wss} for cname, wss in sorted(clients.items())]
    # Dropdown lists
    all_clients = [c.name for c in db.query(Client).order_by(Client.name)]
    all_ram = sorted(set(ws.ram_gb for ws in db.query(Workstation) if ws.ram_gb))
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "clients": clients_list,
        "technicians": TECHNICIANS,
        "statuses": STATUS_LIST,
        "all_clients": all_clients,
        "all_ram": all_ram,
        "filter_client": client,
        "filter_ram": ram,
        "filter_technician": technician,
        "filter_status": status,
        "search": search
    })

@app.post("/update", response_class=HTMLResponse)
async def update_ws(
    id: int = Form(...), field: str = Form(...), value: str = Form(...), db=Depends(get_db)
):
    ws = db.query(Workstation).filter_by(id=id).first()
    if not ws:
        return {"success": False, "msg": "Not found"}
    if field in {"status", "technician", "notes"}:
        setattr(ws, field, value)
        db.commit()
        return {"success": True}
    return {"success": False, "msg": "Invalid field"}

@app.post("/import", response_class=HTMLResponse)
async def import_csv(file: UploadFile = File(...), db=Depends(get_db)):
    file_location = "uploaded.csv"
    with open(file_location, "wb") as f:
        f.write(await file.read())
    import_csv_to_db(file_location, db)
    os.remove(file_location)
    return RedirectResponse(url="/", status_code=303)

@app.get("/export")
def export(
    client: str = "",
    ram: str = "",
    technician: str = "",
    status: str = "",
    search: str = "",
    export_type: str = "csv",
    db=Depends(get_db)
):
    from sqlalchemy import func
    ws_query = db.query(Workstation).options(joinedload(Workstation.client))
    if client:
        ws_query = ws_query.join(Client).filter(func.lower(Client.name).like(f"%{client.lower()}%"))
    if ram:
        ws_query = ws_query.filter(func.lower(Workstation.ram_gb).like(f"%{ram.lower()}%"))
    if technician:
        ws_query = ws_query.filter(func.lower(Workstation.technician).like(f"%{technician.lower()}%"))
    if status:
        ws_query = ws_query.filter(func.lower(Workstation.status).like(f"%{status.lower()}%"))
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
    buf, mime, fname = export_workstations(workstations, export_type)
    return StreamingResponse(buf, media_type=mime, headers={
        "Content-Disposition": f"attachment; filename={fname}"
    })