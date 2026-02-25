from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from db.base import ContractStatus

class CreditApplicationRequest(BaseModel):
    amount_requested: float
    supplier_db_id: Optional[int] = None # Optional supplier reference

class ContractBase(BaseModel):
    merchant_id: str
    amount_requested: float
    supplier_db_id: Optional[int] = None # Optional supplier reference
    status: ContractStatus = ContractStatus.PENDING

class ContractCreate(CreditApplicationRequest):
    pass

class ContractDB(ContractBase):
    id: int
    merchant_db_id: int
    amount_approved: Optional[float] = None
    request_date: datetime
    approval_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    total_repaid: float

    class Config:
        from_attributes = True