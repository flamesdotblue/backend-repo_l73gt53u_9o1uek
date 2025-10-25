"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- Item -> "item" collection
- Consumption -> "consumption" collection
"""

from pydantic import BaseModel, Field
from typing import Optional
import datetime as dt

# Core domain schemas

class Item(BaseModel):
    """Food item definition with unit and protein per unit"""
    name: str = Field(..., description="Item name, e.g., Chicken Breast")
    unit: str = Field(..., description="Unit of measurement, e.g., gm, cup, roti")
    protein_per_unit: float = Field(..., gt=0, description="Protein grams per 1 unit")


class Consumption(BaseModel):
    """A single consumption entry for a specific date"""
    date: dt.date = Field(..., description="The calendar date of consumption")
    item_id: str = Field(..., description="Reference to the item _id (string)")
    quantity: float = Field(..., gt=0, description="How many units consumed on that date")


# Optional response models (used in route responses)
class ItemOut(BaseModel):
    id: str
    name: str
    unit: str
    protein_per_unit: float

class ConsumptionOut(BaseModel):
    id: str
    date: dt.date
    item_id: str
    item_name: str
    unit: str
    quantity: float
    protein_per_unit: float
    protein_total: float
