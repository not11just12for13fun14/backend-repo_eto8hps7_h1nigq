import os
from datetime import date, datetime
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import db, create_document, get_documents

app = FastAPI(title="Journaling API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class UpsertUser(BaseModel):
    email: str
    name: str
    avatar: Optional[str] = None
    bio: Optional[str] = None
    theme: str = "aurora"
    font: str = "Inter"
    goals: List[str] = []


class CreateEntry(BaseModel):
    user_email: str
    date: date
    mood: Optional[str] = None
    answers: Dict[str, str] = {}
    thoughts: Optional[str] = None
    metrics: Dict[str, Any] = {}
    tags: List[str] = []


class UpdateEntry(BaseModel):
    id: str
    mood: Optional[str] = None
    answers: Optional[Dict[str, str]] = None
    thoughts: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    doodle: Optional[Dict[str, Any]] = None


class CreateTodo(BaseModel):
    user_email: str
    date: date
    title: str
    done: bool = False
    notes: Optional[str] = None


class UpdateTodo(BaseModel):
    id: str
    title: Optional[str] = None
    done: Optional[bool] = None
    notes: Optional[str] = None


@app.get("/")
def read_root():
    return {"message": "Journaling Backend Running"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_name"] = db.name
            try:
                response["collections"] = db.list_collection_names()
                response["database"] = "✅ Connected & Working"
                response["connection_status"] = "Connected"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️ Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response


# ---------- Users ----------
@app.get("/api/users")
def get_user(email: str = Query(...)):
    doc = db["user"].find_one({"email": email}) if db else None
    if not doc:
        return {"user": None}
    doc["_id"] = str(doc["_id"])
    return {"user": doc}


@app.post("/api/users")
def upsert_user(payload: UpsertUser):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    now = datetime.utcnow()
    update = {**payload.model_dump(), "updated_at": now}
    res = db["user"].find_one_and_update(
        {"email": payload.email},
        {"$set": update, "$setOnInsert": {"created_at": now}},
        upsert=True,
        return_document=True,
    )
    if res is None:
        # fetch after upsert when driver returns None
        res = db["user"].find_one({"email": payload.email})
    res["_id"] = str(res["_id"]) if res and "_id" in res else None
    return {"user": res}


# ---------- Entries ----------
@app.post("/api/entries")
def create_entry(payload: CreateEntry):
    doc = payload.model_dump()
    entry_id = create_document("entry", doc)
    return {"id": entry_id}


@app.get("/api/entries")
def list_entries(email: str, start: Optional[date] = None, end: Optional[date] = None, on: Optional[date] = None):
    filt: Dict[str, Any] = {"user_email": email}
    if on:
        filt["date"] = on
    else:
        if start and end:
            filt["date"] = {"$gte": start, "$lte": end}
    items = get_documents("entry", filt)
    for it in items:
        it["_id"] = str(it.get("_id"))
    return {"entries": items}


@app.put("/api/entries")
def update_entry(payload: UpdateEntry):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    from bson import ObjectId
    try:
        oid = ObjectId(payload.id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")
    update = {k: v for k, v in payload.model_dump(exclude={"id"}).items() if v is not None}
    update["updated_at"] = datetime.utcnow()
    res = db["entry"].find_one_and_update({"_id": oid}, {"$set": update}, return_document=True)
    if not res:
        raise HTTPException(status_code=404, detail="Entry not found")
    res["_id"] = str(res["_id"])
    return {"entry": res}


@app.delete("/api/entries")
def delete_entry(id: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    from bson import ObjectId
    try:
        oid = ObjectId(id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")
    res = db["entry"].delete_one({"_id": oid})
    return {"deleted": res.deleted_count == 1}


# ---------- Todos ----------
@app.post("/api/todos")
def create_todo(payload: CreateTodo):
    todo_id = create_document("todo", payload.model_dump())
    return {"id": todo_id}


@app.get("/api/todos")
def list_todos(email: str, on: Optional[date] = None, start: Optional[date] = None, end: Optional[date] = None):
    filt: Dict[str, Any] = {"user_email": email}
    if on:
        filt["date"] = on
    elif start and end:
        filt["date"] = {"$gte": start, "$lte": end}
    items = get_documents("todo", filt)
    for it in items:
        it["_id"] = str(it.get("_id"))
    return {"todos": items}


@app.patch("/api/todos")
def update_todo(payload: UpdateTodo):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    from bson import ObjectId
    try:
        oid = ObjectId(payload.id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")
    update = {k: v for k, v in payload.model_dump(exclude={"id"}).items() if v is not None}
    update["updated_at"] = datetime.utcnow()
    res = db["todo"].find_one_and_update({"_id": oid}, {"$set": update}, return_document=True)
    if not res:
        raise HTTPException(status_code=404, detail="Todo not found")
    res["_id"] = str(res["_id"])
    return {"todo": res}


@app.delete("/api/todos")
def delete_todo(id: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    from bson import ObjectId
    try:
        oid = ObjectId(id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")
    res = db["todo"].delete_one({"_id": oid})
    return {"deleted": res.deleted_count == 1}


# ---------- Doodle Generation ----------
class DoodleRequest(BaseModel):
    text: Optional[str] = None
    answers: Dict[str, str] = {}
    metrics: Dict[str, Any] = {}


@app.post("/api/doodle/generate")
def generate_doodle(req: DoodleRequest):
    # Simple keyword extraction
    import re
    content = " ".join([req.text or ""] + list(req.answers.values()))
    tokens = re.findall(r"[a-zA-Z']+", content.lower())
    stop = set("the a an and or but if to of for with on in at from by is are am was were be been being i me my we our you your they their it its this that these those".split())
    words = [t for t in tokens if t not in stop and len(t) > 2]

    # Frequency
    from collections import Counter
    counts = Counter(words)
    top = [w for w, _ in counts.most_common(8)]

    # Map to characters/elements
    library = {
        "coffee": {"type": "element", "name": "coffee-cup"},
        "friend": {"type": "character", "name": "friend"},
        "friends": {"type": "character", "name": "friends"},
        "gym": {"type": "element", "name": "dumbbell"},
        "run": {"type": "element", "name": "running-shoe"},
        "walk": {"type": "element", "name": "footsteps"},
        "family": {"type": "character", "name": "family"},
        "work": {"type": "element", "name": "laptop"},
        "study": {"type": "element", "name": "book"},
        "dog": {"type": "character", "name": "dog"},
        "cat": {"type": "character", "name": "cat"},
        "movie": {"type": "element", "name": "film-reel"},
        "nature": {"type": "element", "name": "leaf"},
        "sleep": {"type": "element", "name": "moon"},
        "sun": {"type": "element", "name": "sun"},
        "beach": {"type": "element", "name": "wave"},
        "party": {"type": "element", "name": "balloons"},
        "cook": {"type": "element", "name": "chef-hat"},
        "bake": {"type": "element", "name": "cupcake"},
        "happy": {"type": "character", "name": "smiley"},
        "grateful": {"type": "element", "name": "sparkles"},
    }

    elements = []
    for w in top:
        if w in library:
            elements.append(library[w])
        else:
            elements.append({"type": "tag", "name": w})

    # Layout positions simple grid
    canvas = []
    cols = 4
    for i, el in enumerate(elements):
        canvas.append({
            **el,
            "x": (i % cols) * 96 + 32,
            "y": (i // cols) * 96 + 32,
            "size": 64,
        })

    palette = "sunset" if req.metrics.get("mood") in ("happy", "grateful", "excited") else "midnight"

    return {"doodle": {"palette": palette, "items": canvas, "keywords": top}}


# ---------- Affirmations ----------
AFFIRMATIONS = [
    "You are growing exactly at the pace you need.",
    "Small steps today create big shifts over time.",
    "Your feelings are valid and your voice matters.",
    "You have permission to rest and recalibrate.",
    "Progress, not perfection.",
    "You are resilient, creative, and kind to yourself.",
    "Your mind and body deserve gentle care today.",
]


@app.get("/api/affirmation/daily")
def daily_affirmation(email: Optional[str] = None, on: Optional[date] = None):
    seed_str = (email or "anon") + (on.isoformat() if on else date.today().isoformat())
    idx = sum(ord(c) for c in seed_str) % len(AFFIRMATIONS)
    return {"affirmation": AFFIRMATIONS[idx]}


# ---------- Insights ----------
@app.get("/api/insights/summary")
def insights_summary(email: str, start: Optional[date] = None, end: Optional[date] = None):
    filt: Dict[str, Any] = {"user_email": email}
    if start and end:
        filt["date"] = {"$gte": start, "$lte": end}
    items = get_documents("entry", filt)
    # Mood counts
    mood_counts: Dict[str, int] = {}
    metrics_acc: Dict[str, List[float]] = {}
    for e in items:
        m = (e.get("mood") or "unknown").lower()
        mood_counts[m] = mood_counts.get(m, 0) + 1
        for k, v in (e.get("metrics") or {}).items():
            try:
                metrics_acc.setdefault(k, []).append(float(v))
            except Exception:
                pass
    metrics_avg = {k: (sum(v) / len(v) if v else 0) for k, v in metrics_acc.items()}
    for it in items:
        it["_id"] = str(it.get("_id"))
    return {"mood": mood_counts, "metrics_avg": metrics_avg, "count": len(items)}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
