from sqlalchemy.orm import Session
from db.base import Contract, Merchant, ContractStatus
from models.contract import ContractCreate
from datetime import datetime, timedelta

def create_contract(db: Session, contract: ContractCreate, amount_approved: float, merchant_db_id: int, merchant_id: str = None, supplier_db_id: int = None):
    """
    Creates a new contract record in the database.
    """
    # Calculate due date (e.g., 30 days from request)
    due_date = datetime.utcnow() + timedelta(days=30) # Using UTC for consistency

    db_contract = Contract(
        merchant_db_id=merchant_db_id,
        merchant_id=merchant_id if merchant_id else getattr(contract, 'merchant_id', None),
        supplier_db_id=supplier_db_id if supplier_db_id else getattr(contract, 'supplier_db_id', None),
        amount_requested=contract.amount_requested,
        amount_approved=amount_approved,
        status=ContractStatus.APPROVED.value, # Status is APPROVED on creation if it passes checks
        approval_date=datetime.utcnow(),
        due_date=due_date
    )
    db.add(db_contract)
    db.commit()
    db.refresh(db_contract)
    return db_contract

def get_contracts_by_merchant_id(db: Session, merchant_id: str):
    """
    Retrieves all contracts for a given merchant_id.
    """
    return db.query(Contract).filter(Contract.merchant_id == merchant_id).all()

def get_active_contracts_for_merchant(db: Session, merchant_id: str):
    """
    Retrieves active contracts for a given merchant_id (not settled or rejected).
    """
    return db.query(Contract).filter(
        Contract.merchant_id == merchant_id,
        Contract.status.notin_([ContractStatus.SETTLED.value, ContractStatus.REJECTED.value])
    ).all()

def get_contracts_by_supplier_id(db: Session, supplier_db_id: int):
    """
    Retrieves all contracts for a given supplier_db_id.
    """
    return db.query(Contract).filter(Contract.supplier_db_id == supplier_db_id).all()

def get_active_contracts_for_supplier(db: Session, supplier_db_id: int):
    """
    Retrieves active contracts for a given supplier_db_id (not settled or rejected).
    """
    return db.query(Contract).filter(
        Contract.supplier_db_id == supplier_db_id,
        Contract.status.notin_([ContractStatus.SETTLED.value, ContractStatus.REJECTED.value])
    ).all()
