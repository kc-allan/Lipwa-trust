from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# --- Pydantic Schemas ---

class SupplierBase(BaseModel):
    supplier_id: str
    name: str
    contact_person: str
    phone_number: str
    email: Optional[str] = None
    product_category: Optional[str] = None # Category of products/services supplied

class SupplierCreate(SupplierBase):
    supplier_id: Optional[str] = None # Make supplier_id optional for creation

class SupplierDB(SupplierBase):
    id: int
    onboarded_at: datetime

    class Config:
        from_attributes = True


