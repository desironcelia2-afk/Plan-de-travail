from fastapi import FastAPI, APIRouter, HTTPException, Header
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime, timezone


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'maitresse')

app = FastAPI()
api_router = APIRouter(prefix="/api")


# ========== Models ==========
class Child(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    emoji: str = "🦊"
    color: str = "#FDE68A"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ChildCreate(BaseModel):
    name: str
    emoji: Optional[str] = "🦊"
    color: Optional[str] = "#FDE68A"


class Workshop(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    emoji: str = "🎨"
    color: str = "#BFDBFE"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class WorkshopCreate(BaseModel):
    name: str
    emoji: Optional[str] = "🎨"
    color: Optional[str] = "#BFDBFE"


class ValidationRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    child_id: str
    workshop_id: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ValidationCreate(BaseModel):
    child_id: str
    workshop_id: str


class AdminLogin(BaseModel):
    password: str


class WorkshopStatus(BaseModel):
    workshop: Workshop
    done: bool
    last_done_at: Optional[str] = None


# ========== Auth helper ==========
def verify_admin(x_admin_password: Optional[str]):
    if x_admin_password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Mot de passe admin incorrect")


# ========== Routes ==========
@api_router.get("/")
async def root():
    return {"message": "Ateliers Autonomes API"}


@api_router.post("/admin/login")
async def admin_login(payload: AdminLogin):
    if payload.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Mot de passe incorrect")
    return {"success": True}


# ----- Children -----
@api_router.get("/children", response_model=List[Child])
async def list_children():
    docs = await db.children.find({}, {"_id": 0}).sort("name", 1).to_list(1000)
    return docs


@api_router.post("/children", response_model=Child)
async def create_child(payload: ChildCreate, x_admin_password: Optional[str] = Header(None)):
    verify_admin(x_admin_password)
    child = Child(**payload.model_dump())
    await db.children.insert_one(child.model_dump())
    return child


@api_router.delete("/children/{child_id}")
async def delete_child(child_id: str, x_admin_password: Optional[str] = Header(None)):
    verify_admin(x_admin_password)
    result = await db.children.delete_one({"id": child_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Enfant introuvable")
    await db.validations.delete_many({"child_id": child_id})
    return {"success": True}


@api_router.get("/children/{child_id}", response_model=Child)
async def get_child(child_id: str):
    doc = await db.children.find_one({"id": child_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Enfant introuvable")
    return doc


# ----- Workshops -----
@api_router.get("/workshops", response_model=List[Workshop])
async def list_workshops():
    docs = await db.workshops.find({}, {"_id": 0}).sort("created_at", 1).to_list(1000)
    return docs


@api_router.post("/workshops", response_model=Workshop)
async def create_workshop(payload: WorkshopCreate, x_admin_password: Optional[str] = Header(None)):
    verify_admin(x_admin_password)
    workshop = Workshop(**payload.model_dump())
    await db.workshops.insert_one(workshop.model_dump())
    return workshop


@api_router.delete("/workshops/{workshop_id}")
async def delete_workshop(workshop_id: str, x_admin_password: Optional[str] = Header(None)):
    verify_admin(x_admin_password)
    result = await db.workshops.delete_one({"id": workshop_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Atelier introuvable")
    await db.validations.delete_many({"workshop_id": workshop_id})
    return {"success": True}


# ----- Validations -----
@api_router.get("/children/{child_id}/status", response_model=List[WorkshopStatus])
async def child_status(child_id: str):
    child = await db.children.find_one({"id": child_id}, {"_id": 0})
    if not child:
        raise HTTPException(status_code=404, detail="Enfant introuvable")

    workshops = await db.workshops.find({}, {"_id": 0}).sort("created_at", 1).to_list(1000)
    validations = await db.validations.find({"child_id": child_id}, {"_id": 0}).to_list(10000)

    latest = {}
    for v in validations:
        wid = v["workshop_id"]
        ts = v["timestamp"]
        if wid not in latest or ts > latest[wid]:
            latest[wid] = ts

    return [
        WorkshopStatus(
            workshop=Workshop(**w),
            done=w["id"] in latest,
            last_done_at=latest.get(w["id"]),
        )
        for w in workshops
    ]


@api_router.post("/validations")
async def add_validation(payload: ValidationCreate):
    child = await db.children.find_one({"id": payload.child_id}, {"_id": 0})
    if not child:
        raise HTTPException(status_code=404, detail="Enfant introuvable")
    workshop = await db.workshops.find_one({"id": payload.workshop_id}, {"_id": 0})
    if not workshop:
        raise HTTPException(status_code=404, detail="Atelier introuvable")

    record = ValidationRecord(
        child_id=payload.child_id,
        workshop_id=payload.workshop_id,
    )
    await db.validations.insert_one(record.model_dump())
    return {"success": True, "id": record.id, "timestamp": record.timestamp}


@api_router.delete("/validations")
async def remove_validation(child_id: str, workshop_id: str):
    # Remove ALL validation records for this pair (un-validate completely)
    result = await db.validations.delete_many(
        {"child_id": child_id, "workshop_id": workshop_id}
    )
    return {"success": True, "deleted": result.deleted_count}


# ----- Admin overview -----
@api_router.get("/admin/overview")
async def admin_overview(x_admin_password: Optional[str] = Header(None)):
    verify_admin(x_admin_password)
    children = await db.children.find({}, {"_id": 0}).sort("name", 1).to_list(1000)
    workshops = await db.workshops.find({}, {"_id": 0}).sort("created_at", 1).to_list(1000)
    validations = await db.validations.find({}, {"_id": 0}).to_list(100000)

    done_map = {}  # child_id -> set of workshop_ids
    for v in validations:
        done_map.setdefault(v["child_id"], set()).add(v["workshop_id"])

    rows = []
    for c in children:
        done_ids = done_map.get(c["id"], set())
        rows.append({
            "child": c,
            "done_workshop_ids": list(done_ids),
            "done_count": len(done_ids),
            "total": len(workshops),
        })

    return {"workshops": workshops, "rows": rows}


# ----- Seed default data if empty -----
@app.on_event("startup")
async def seed_default_data():
    count_children = await db.children.count_documents({})
    if count_children == 0:
        defaults = [
            ("Léa", "🦊", "#FDE68A"),
            ("Tom", "🐻", "#BFDBFE"),
            ("Chloé", "🐰", "#FBCFE8"),
            ("Noah", "🦁", "#FED7AA"),
            ("Emma", "🦄", "#DDD6FE"),
            ("Lucas", "🐼", "#BBF7D0"),
        ]
        await db.children.insert_many([
            Child(name=n, emoji=e, color=c).model_dump() for n, e, c in defaults
        ])

    count_workshops = await db.workshops.count_documents({})
    if count_workshops == 0:
        defaults_ws = [
            ("Peinture", "🎨", "#FCA5A5"),
            ("Puzzle", "🧩", "#93C5FD"),
            ("Pâte à modeler", "🧶", "#FDBA74"),
            ("Lettres", "🔤", "#86EFAC"),
            ("Chiffres", "🔢", "#C4B5FD"),
            ("Collage", "✂️", "#F9A8D4"),
            ("Livre", "📚", "#FCD34D"),
            ("Construction", "🧱", "#67E8F9"),
        ]
        await db.workshops.insert_many([
            Workshop(name=n, emoji=e, color=c).model_dump() for n, e, c in defaults_ws
        ])


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
