import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Dict, Any
from datetime import date

from database import db, create_document, get_documents
from schemas import Item, Consumption, ItemOut, ConsumptionOut

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Protein Tracker API is running"}


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
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


# Utility

def oid(id_str: str):
    # Import locally to avoid startup failures if bson isn't available for any reason
    try:
        from bson import ObjectId  # provided by pymongo
    except Exception as e:
        raise HTTPException(status_code=500, detail="ObjectId support not available")
    try:
        return ObjectId(id_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID format")


def serialize_item(doc: Dict[str, Any]) -> ItemOut:
    return ItemOut(
        id=str(doc.get("_id")),
        name=doc.get("name"),
        unit=doc.get("unit"),
        protein_per_unit=float(doc.get("protein_per_unit", 0)),
    )


# Items endpoints
@app.post("/api/items", response_model=ItemOut)
def create_item(item: Item):
    existing = db["item"].find_one({"name": item.name})
    if existing:
        raise HTTPException(status_code=400, detail="Item with this name already exists")

    new_id = create_document("item", item)
    doc = db["item"].find_one({"_id": oid(new_id)})
    return serialize_item(doc)


@app.get("/api/items", response_model=List[ItemOut])
def list_items():
    docs = get_documents("item", {})
    return [serialize_item(d) for d in docs]


# Consumption endpoints
@app.post("/api/consumptions", response_model=ConsumptionOut)
def create_consumption(entry: Consumption):
    item_doc = db["item"].find_one({"_id": oid(entry.item_id)})
    if not item_doc:
        raise HTTPException(status_code=404, detail="Item not found")

    protein_per_unit = float(item_doc.get("protein_per_unit", 0))
    protein_total = protein_per_unit * entry.quantity

    payload = {
        "date": entry.date.isoformat(),
        "item_id": entry.item_id,
        "item_name": item_doc.get("name"),
        "unit": item_doc.get("unit"),
        "quantity": entry.quantity,
        "protein_per_unit": protein_per_unit,
        "protein_total": protein_total,
    }

    new_id = create_document("consumption", payload)
    saved = db["consumption"].find_one({"_id": oid(new_id)})

    return ConsumptionOut(
        id=str(saved.get("_id")),
        date=date.fromisoformat(saved.get("date")),
        item_id=saved.get("item_id"),
        item_name=saved.get("item_name"),
        unit=saved.get("unit"),
        quantity=float(saved.get("quantity", 0)),
        protein_per_unit=float(saved.get("protein_per_unit", 0)),
        protein_total=float(saved.get("protein_total", 0)),
    )


@app.get("/api/consumptions", response_model=Dict[str, Any])
def list_consumptions(date_str: str = Query(..., alias="date")):
    try:
        _ = date.fromisoformat(date_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    docs = get_documents("consumption", {"date": date_str})
    entries: List[ConsumptionOut] = []
    total_protein = 0.0

    for d in docs:
        co = ConsumptionOut(
            id=str(d.get("_id")),
            date=date.fromisoformat(d.get("date")),
            item_id=d.get("item_id"),
            item_name=d.get("item_name"),
            unit=d.get("unit"),
            quantity=float(d.get("quantity", 0)),
            protein_per_unit=float(d.get("protein_per_unit", 0)),
            protein_total=float(d.get("protein_total", 0)),
        )
        entries.append(co)
        total_protein += co.protein_total

    return {
        "date": date_str,
        "entries": [e.model_dump() for e in entries],
        "total_protein": round(total_protein, 2),
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
