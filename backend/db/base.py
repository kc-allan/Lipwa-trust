from sqlalchemy import Boolean, Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql import func
from enum import Enum

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_merchant = Column(Boolean, default=False)
    is_supplier = Column(Boolean, default=False)

    merchant_profile = relationship("Merchant", back_populates="user", uselist=False)
    supplier_profile = relationship("Supplier", back_populates="user", uselist=False)

class Merchant(Base):
    __tablename__ = "merchants"

    id = Column(Integer, primary_key=True, index=True)
    merchant_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    business_type = Column(String)
    contact_person = Column(String)
    phone_number = Column(String)
    email = Column(String, nullable=True)
    
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=True) # Link to User
    user = relationship("User", back_populates="merchant_profile") # Relationship

    # Data for trust score
    avg_daily_sales = Column(Float, nullable=False)
    consistency = Column(Float, nullable=False)
    days_active = Column(Integer, nullable=False)

    # Calculated fields
    trust_score = Column(Integer, nullable=True)
    credit_limit = Column(Float, nullable=True)
    
    onboarded_at = Column(DateTime(timezone=True), server_default=func.now())

    contracts = relationship("Contract", back_populates="merchant")

class ContractStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    DISPATCHED = "DISPATCHED"
    DELIVERED = "DELIVERED"
    SETTLED = "SETTLED"
    OVERDUE = "OVERDUE"

class Contract(Base):
    __tablename__ = "contracts"

    id = Column(Integer, primary_key=True, index=True)
    merchant_db_id = Column(Integer, ForeignKey("merchants.id"), nullable=False)
    merchant_id = Column(String, nullable=False, index=True) # Redundant but useful for direct lookup
    supplier_db_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True) # Link to supplier (optional initially)
    
    amount_requested = Column(Float, nullable=False)
    amount_approved = Column(Float, nullable=True)
    status = Column(String, default=ContractStatus.PENDING.value, nullable=False)
    
    request_date = Column(DateTime(timezone=True), server_default=func.now())
    approval_date = Column(DateTime(timezone=True), nullable=True)
    due_date = Column(DateTime(timezone=True), nullable=True) # Expected repayment date
    
    # Repayment tracking
    total_repaid = Column(Float, default=0.0, nullable=False)
    
    merchant = relationship("Merchant", back_populates="contracts")
    supplier = relationship("Supplier", back_populates="contracts") # Added relationship
    repayments = relationship("Repayment", back_populates="contract") # Added relationship

class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    contact_person = Column(String)
    phone_number = Column(String)
    email = Column(String, nullable=True)
    product_category = Column(String, nullable=True) # Category of products/services supplied (e.g., "Wholesale Groceries", "Electronics")
    
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=True) # Link to User
    user = relationship("User", back_populates="supplier_profile") # Relationship
    
    onboarded_at = Column(DateTime(timezone=True), server_default=func.now())
    
    contracts = relationship("Contract", back_populates="supplier") # Relationship to contracts

class Repayment(Base):
    __tablename__ = "repayments"

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False)
    amount = Column(Float, nullable=False)
    repayment_date = Column(DateTime(timezone=True), server_default=func.now())

    contract = relationship("Contract", back_populates="repayments")
