from fastapi import FastAPI, APIRouter, HTTPException, Header, UploadFile, File, Response
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
import requests


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'maitresse')

# ===== Object Storage =====
STORAGE_URL = "https://integrations.emergentagent.com/objstore/api/v1/storage"
EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY")
APP_NAME = os.environ.get("APP_NAME", "maternelle-ateliers")
_storage_key: Optional[str] = None

MIME_TYPES = {
    "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
    "gif": "image/gif", "webp": "image/webp",
}


def init_storage():
    global _storage_key
    if _storage_key:
        return _storage_key
    resp = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": EMERGENT_KEY}, timeout=30)
    resp.raise_for_status()
    _storage_key = resp.json()["storage_key"]
    return _storage_key


def put_object(path: str, data: bytes, content_type: str) -> dict:
    key = init_storage()
    resp = requests.put(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key, "Content-Type": content_type},
        data=data, timeout=120,
    )
    resp.raise_for_status()
    return resp.json()


def get_object(path: str):
    key = init_storage()
    resp = requests.get(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key}, timeout=60,
    )
    resp.raise_for_status()
    return resp.content, resp.headers.get("Content-Type", "application/octet-stream")

app = FastAPI()
api_router = APIRouter(prefix="/api")


# ========== Models ==========
class Child(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    emoji: str = "🦊"
    color: str = "#FDE68A"
    photo_url: Optional[str] = None
    class_id: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ChildCreate(BaseModel):
    name: str
    emoji: Optional[str] = "🦊"
    color: Optional[str] = "#FDE68A"
    class_id: str


class ChildUpdate(BaseModel):
    name: Optional[str] = None
    emoji: Optional[str] = None
    color: Optional[str] = None
    class_id: Optional[str] = None


class ClassRoom(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    emoji: str = "🏫"
    color: str = "#DBEAFE"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ClassRoomCreate(BaseModel):
    name: str
    emoji: Optional[str] = "🏫"
    color: Optional[str] = "#DBEAFE"


class Workshop(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    emoji: str = "🎨"
    color: str = "#BFDBFE"
    photo_url: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class WorkshopCreate(BaseModel):
    name: str
    emoji: Optional[str] = "🎨"
    color: Optional[str] = "#BFDBFE"


class WorkshopUpdate(BaseModel):
    name: Optional[str] = None
    emoji: Optional[str] = None
    color: Optional[str] = None


class ClassRoomUpdate(BaseModel):
    name: Optional[str] = None
    emoji: Optional[str] = None
    color: Optional[str] = None


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
    # Auth disabled per product decision — app used on classroom whiteboard,
    # espace maîtresse is open access. Kept for future reintroduction.
    return True


# ========== Routes ==========
@api_router.get("/")
async def root():
    return {"message": "Ateliers Autonomes API"}


@api_router.post("/admin/login")
async def admin_login(payload: AdminLogin):
    if payload.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Mot de passe incorrect")
    return {"success": True}


# ----- Classes -----
@api_router.get("/classes", response_model=List[ClassRoom])
async def list_classes():
    docs = await db.classes.find({}, {"_id": 0}).sort("created_at", 1).to_list(1000)
    return docs


@api_router.post("/classes", response_model=ClassRoom)
async def create_class(payload: ClassRoomCreate, x_admin_password: Optional[str] = Header(None)):
    verify_admin(x_admin_password)
    klass = ClassRoom(**payload.model_dump())
    await db.classes.insert_one(klass.model_dump())
    return klass


@api_router.patch("/classes/{class_id}", response_model=ClassRoom)
async def update_class(class_id: str, payload: ClassRoomUpdate, x_admin_password: Optional[str] = Header(None)):
    verify_admin(x_admin_password)
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="Aucune modification")
    result = await db.classes.update_one({"id": class_id}, {"$set": updates})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Classe introuvable")
    doc = await db.classes.find_one({"id": class_id}, {"_id": 0})
    return doc


@api_router.delete("/classes/{class_id}")
async def delete_class(class_id: str, x_admin_password: Optional[str] = Header(None)):
    verify_admin(x_admin_password)
    # Prevent deleting the last class
    total = await db.classes.count_documents({})
    if total <= 1:
        raise HTTPException(status_code=400, detail="Impossible de supprimer la dernière classe")
    result = await db.classes.delete_one({"id": class_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Classe introuvable")
    # Cascade: delete children of this class + their validations
    children_ids = [
        c["id"] async for c in db.children.find({"class_id": class_id}, {"_id": 0, "id": 1})
    ]
    if children_ids:
        await db.validations.delete_many({"child_id": {"$in": children_ids}})
        await db.children.delete_many({"class_id": class_id})
    return {"success": True}


@api_router.get("/classes/{class_id}", response_model=ClassRoom)
async def get_class(class_id: str):
    doc = await db.classes.find_one({"id": class_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Classe introuvable")
    return doc


# ----- Children -----
@api_router.get("/children", response_model=List[Child])
async def list_children(class_id: Optional[str] = None):
    query = {"class_id": class_id} if class_id else {}
    docs = await db.children.find(query, {"_id": 0}).sort("name", 1).to_list(1000)
    return docs


@api_router.post("/children", response_model=Child)
async def create_child(payload: ChildCreate, x_admin_password: Optional[str] = Header(None)):
    verify_admin(x_admin_password)
    klass = await db.classes.find_one({"id": payload.class_id}, {"_id": 0})
    if not klass:
        raise HTTPException(status_code=400, detail="Classe invalide")
    child = Child(**payload.model_dump())
    await db.children.insert_one(child.model_dump())
    return child


@api_router.patch("/children/{child_id}", response_model=Child)
async def update_child(child_id: str, payload: ChildUpdate, x_admin_password: Optional[str] = Header(None)):
    verify_admin(x_admin_password)
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="Aucune modification")
    if "class_id" in updates:
        klass = await db.classes.find_one({"id": updates["class_id"]}, {"_id": 0})
        if not klass:
            raise HTTPException(status_code=400, detail="Classe invalide")
    result = await db.children.update_one({"id": child_id}, {"$set": updates})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Enfant introuvable")
    doc = await db.children.find_one({"id": child_id}, {"_id": 0})
    return doc


@api_router.delete("/children")
async def delete_all_children(class_id: Optional[str] = None, x_admin_password: Optional[str] = Header(None)):
    verify_admin(x_admin_password)
    query = {"class_id": class_id} if class_id else {}
    children_ids = [c["id"] async for c in db.children.find(query, {"_id": 0, "id": 1})]
    if children_ids:
        await db.validations.delete_many({"child_id": {"$in": children_ids}})
    result = await db.children.delete_many(query)
    return {"success": True, "deleted": result.deleted_count}


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


@api_router.patch("/workshops/{workshop_id}", response_model=Workshop)
async def update_workshop(workshop_id: str, payload: WorkshopUpdate, x_admin_password: Optional[str] = Header(None)):
    verify_admin(x_admin_password)
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="Aucune modification")
    result = await db.workshops.update_one({"id": workshop_id}, {"$set": updates})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Atelier introuvable")
    doc = await db.workshops.find_one({"id": workshop_id}, {"_id": 0})
    return doc


@api_router.delete("/workshops")
async def delete_all_workshops(x_admin_password: Optional[str] = Header(None)):
    verify_admin(x_admin_password)
    workshop_ids = [w["id"] async for w in db.workshops.find({}, {"_id": 0, "id": 1})]
    if workshop_ids:
        await db.validations.delete_many({"workshop_id": {"$in": workshop_ids}})
    result = await db.workshops.delete_many({})
    return {"success": True, "deleted": result.deleted_count}


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
    validations = await db.validations.find(
        {"child_id": child_id},
        {"_id": 0, "workshop_id": 1, "timestamp": 1},
    ).to_list(2000)

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
async def admin_overview(class_id: Optional[str] = None, x_admin_password: Optional[str] = Header(None)):
    verify_admin(x_admin_password)
    child_query = {"class_id": class_id} if class_id else {}
    children = await db.children.find(child_query, {"_id": 0}).sort("name", 1).to_list(1000)
    workshops = await db.workshops.find({}, {"_id": 0}).sort("created_at", 1).to_list(1000)
    child_ids = [c["id"] for c in children]
    validation_query = {"child_id": {"$in": child_ids}} if child_ids else {"child_id": {"$in": []}}
    validations = await db.validations.find(
        validation_query,
        {"_id": 0, "child_id": 1, "workshop_id": 1},
    ).to_list(20000)

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


# ----- Photo upload / serve -----
async def _upload_photo_for(entity: str, entity_id: str, file: UploadFile) -> str:
    collection = db.children if entity == "child" else db.workshops
    doc = await collection.find_one({"id": entity_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Introuvable")

    ext = (file.filename or "").rsplit(".", 1)[-1].lower() if "." in (file.filename or "") else "jpg"
    if ext not in MIME_TYPES:
        raise HTTPException(status_code=400, detail="Format image non supporté (jpg/png/webp/gif)")
    content_type = MIME_TYPES[ext]

    data = await file.read()
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image trop lourde (max 5 Mo)")

    storage_path = f"{APP_NAME}/{entity}/{entity_id}/{uuid.uuid4()}.{ext}"
    try:
        put_object(storage_path, data, content_type)
    except Exception as e:
        logger.error(f"Upload storage error: {e}")
        raise HTTPException(status_code=502, detail="Erreur de stockage")

    photo_url = f"/api/files/{storage_path}"
    await collection.update_one({"id": entity_id}, {"$set": {"photo_url": photo_url}})
    return photo_url


@api_router.post("/children/{child_id}/photo")
async def upload_child_photo(
    child_id: str,
    file: UploadFile = File(...),
    x_admin_password: Optional[str] = Header(None),
):
    verify_admin(x_admin_password)
    url = await _upload_photo_for("child", child_id, file)
    return {"success": True, "photo_url": url}


@api_router.post("/workshops/{workshop_id}/photo")
async def upload_workshop_photo(
    workshop_id: str,
    file: UploadFile = File(...),
    x_admin_password: Optional[str] = Header(None),
):
    verify_admin(x_admin_password)
    url = await _upload_photo_for("workshop", workshop_id, file)
    return {"success": True, "photo_url": url}


@api_router.delete("/children/{child_id}/photo")
async def delete_child_photo(child_id: str, x_admin_password: Optional[str] = Header(None)):
    verify_admin(x_admin_password)
    result = await db.children.update_one({"id": child_id}, {"$set": {"photo_url": None}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Enfant introuvable")
    return {"success": True}


@api_router.delete("/workshops/{workshop_id}/photo")
async def delete_workshop_photo(workshop_id: str, x_admin_password: Optional[str] = Header(None)):
    verify_admin(x_admin_password)
    result = await db.workshops.update_one({"id": workshop_id}, {"$set": {"photo_url": None}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Atelier introuvable")
    return {"success": True}


@api_router.get("/files/{path:path}")
async def serve_file(path: str):
    try:
        data, content_type = get_object(path)
    except requests.HTTPError as e:
        status = e.response.status_code if e.response is not None else 500
        raise HTTPException(status_code=404 if status == 404 else 502, detail="Fichier introuvable")
    except Exception:
        raise HTTPException(status_code=502, detail="Erreur de stockage")
    return Response(
        content=data,
        media_type=content_type,
        headers={"Cache-Control": "public, max-age=86400"},
    )


# ----- Seed default data if empty -----
@app.on_event("startup")
async def on_startup():
    # Init object storage (non-fatal if it fails — retried on first upload)
    try:
        init_storage()
        logger.info("Object storage initialized")
    except Exception as e:
        logger.error(f"Storage init failed at startup: {e}")

    # Seed default data
    # Ensure at least one class exists & backfill children without class_id
    count_classes = await db.classes.count_documents({})
    if count_classes == 0:
        default_class = ClassRoom(name="Classe par défaut", emoji="🏫", color="#DBEAFE")
        await db.classes.insert_one(default_class.model_dump())
        default_class_id = default_class.id
    else:
        first = await db.classes.find_one({}, {"_id": 0}, sort=[("created_at", 1)])
        default_class_id = first["id"]

    # Backfill children missing class_id
    await db.children.update_many(
        {"$or": [{"class_id": None}, {"class_id": {"$exists": False}}]},
        {"$set": {"class_id": default_class_id}},
    )

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
            Child(name=n, emoji=e, color=c, class_id=default_class_id).model_dump() for n, e, c in defaults
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
