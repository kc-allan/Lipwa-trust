from fastapi import FastAPI, Depends, HTTPException, status, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta
import random # Needed for generating merchant/supplier IDs

from trust_score_engine import calculate_trust_score
from db.session import SessionLocal, engine
from db.base import Base, Contract, User, ContractStatus # Import User model to use its relationships
from models.merchant import MerchantCreate, MerchantDB, TrustScoreResponse, MerchantDashboard
from models.contract import CreditApplicationRequest, ContractDB
from models.supplier import SupplierCreate, SupplierDB
from models.repayment import RepaymentCreate, RepaymentDB
from models.user import UserCreate, UserInDB, Token
from crud import merchant as crud_merchant
from crud import contract as crud_contract
from crud import supplier as crud_supplier
from crud import repayment as crud_repayment
from crud import user as crud_user
from core.security import verify_password, create_access_token
from core.config import settings
from dependencies import get_current_active_user, get_current_merchant_user, get_current_supplier_user # Import dependencies

app = FastAPI(
    title="Lipwa-Trust Backend",
    description="Backend API for Lipwa-Trust with SQLite integration and JWT Auth.",
    version="0.3.0",
)

# --- CORS Middleware ---
origins = ["*"] # Allow all origins for hackathon MVP

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Database Initialization on Startup ---
@app.on_event("startup")
def on_startup():
    # Create all tables if they don't exist
    # This is for SQLite "drop and recreate" strategy
    Base.metadata.create_all(bind=engine)

# --- Dependency ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Endpoints ---

# Authentication Endpoints
@app.post("/auth/register", response_model=UserInDB, summary="Register a new user")
async def register_user(user: UserCreate, db: Session = Depends(get_db)):
    """
    Registers a new user with their email and password.
    Users can be registered as a merchant or a supplier.
    """
    db_user = crud_user.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    return crud_user.create_user(db=db, user=user)

@app.post("/auth/login", response_model=Token, summary="Log in user and get JWT token")
async def login_for_access_token(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(), # FastAPI's built-in form data parser for OAuth2
    db: Session = Depends(get_db)
):
    """
    Logs in a user with email and password, returning an access token.
    The access token is also set as an HttpOnly cookie.
    """
    user = crud_user.get_user_by_email(db, email=form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "user_id": user.id, "is_merchant": user.is_merchant, "is_supplier": user.is_supplier},
        expires_delta=access_token_expires
    )
    
    response.set_cookie(
        key="access_token", 
        value=access_token, 
        httponly=True, 
        samesite="lax", # Strict, Lax, None. Lax is often a good default.
        secure=False, # Set to True in production for HTTPS
        max_age=int(access_token_expires.total_seconds())
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

# Merchant Endpoints
@app.post("/merchants/onboard", response_model=MerchantDB, summary="Onboard a new merchant (requires login)")
async def onboard_merchant(
    merchant_data: MerchantCreate, # Renamed to avoid clash with request
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Onboards a new merchant into the Lipwa-Trust system, linking it to the logged-in user.
    - User must be logged in and not already a merchant.
    - Calculates an initial trust score and credit limit.
    """
    if current_user.is_merchant:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is already a merchant.")
    if current_user.merchant_profile: # Additional check if profile exists but flag not set
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already has a merchant profile.")

    # Generate a unique merchant_id (since it's no longer from request body)
    generated_merchant_id = f"MER-{random.randint(10000, 99999)}"
    while crud_merchant.get_merchant_by_merchant_id(db, merchant_id=generated_merchant_id):
        generated_merchant_id = f"MER-{random.randint(10000, 99999)}"

    # Create a temporary MerchantCreate object with generated merchant_id
    merchant_data_dict = merchant_data.model_dump()
    merchant_data_dict.pop('merchant_id', None)  # Remove merchant_id if it exists to avoid duplicate keyword argument
    temp_merchant_create = MerchantCreate(merchant_id=generated_merchant_id, **merchant_data_dict)

    score_data = calculate_trust_score(
        merchant_data.avg_daily_sales,
        merchant_data.consistency,
        merchant_data.days_active
    )

    new_merchant = crud_merchant.create_merchant(
        db=db,
        merchant=temp_merchant_create,
        trust_score=score_data["score"],
        credit_limit=score_data["credit_limit"],
        user_id=current_user.id # Link to current user
    )

    # Update user's is_merchant flag
    crud_user.update_user_is_merchant(db, current_user.id, True)
    
    return new_merchant

@app.get("/merchant/me/score", response_model=TrustScoreResponse, summary="Get logged-in merchant's trust score and credit limit")
async def get_my_trust_score(
    current_user: User = Depends(get_current_merchant_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves the current trust score and credit limit for the logged-in merchant.
    """
    merchant = current_user.merchant_profile
    if not merchant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Merchant profile not found for this user.")

    return TrustScoreResponse(
        merchant_id=merchant.merchant_id,
        trust_score=merchant.trust_score,
        credit_limit=merchant.credit_limit
    )

@app.get("/merchant/me/dashboard", response_model=MerchantDashboard, summary="Get full dashboard data for logged-in merchant")
async def get_my_merchant_dashboard(
    current_user: User = Depends(get_current_merchant_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves all relevant data for the logged-in merchant's dashboard,
    including their profile, trust score, credit limit, and all associated contracts.
    """
    merchant = current_user.merchant_profile
    if not merchant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Merchant profile not found for this user.")
    
    contracts = crud_contract.get_contracts_by_merchant_id(db, merchant_id=merchant.merchant_id)
    
    merchant_data = MerchantDB.model_validate(merchant)
    contract_data = [ContractDB.model_validate(c) for c in contracts]
    
    return MerchantDashboard(
        **merchant_data.model_dump(),
        contracts=contract_data
    )

@app.post("/merchant/me/simulate_daily_sales", response_model=MerchantDB, summary="Simulate a day's sales for logged-in merchant and update their trust score")
async def simulate_my_daily_sales(
    current_user: User = Depends(get_current_merchant_user),
    db: Session = Depends(get_db)
):
    """
    Simulates a day's sales activity for the logged-in merchant,
    updating their average daily sales, consistency, days active,
    and recalculating their trust score and credit limit.
    """
    merchant = current_user.merchant_profile
    if not merchant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Merchant profile not found for this user.")
    
    updated_merchant = crud_merchant.update_merchant_sales_and_score(db, merchant)
    return updated_merchant


# Credit Endpoints
@app.post("/credit/apply", response_model=ContractDB, summary="Apply for credit/inventory financing (logged-in merchant)")
async def apply_for_credit(
    request: CreditApplicationRequest,
    current_user: User = Depends(get_current_merchant_user),
    db: Session = Depends(get_db)
):
    """
    Allows the logged-in merchant to apply for credit or inventory financing.
    Performs checks against the merchant's trust score and credit limit.
    """
    merchant = current_user.merchant_profile
    if not merchant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Merchant profile not found for this user.")

    # Basic approval logic for MVP
    min_trust_score_for_credit = 40
    if merchant.trust_score < min_trust_score_for_credit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Trust score too low ({merchant.trust_score}). Minimum required: {min_trust_score_for_credit}."
        )
    
    if request.amount_requested > merchant.credit_limit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Amount requested ({request.amount_requested}) exceeds available credit limit ({merchant.credit_limit})."
        )
    
    # If all checks pass, create the contract
    amount_approved = request.amount_requested # For MVP, assume approved amount is requested amount if passed checks
    new_contract = crud_contract.create_contract(
        db=db,
        contract=request,
        amount_approved=amount_approved,
        merchant_db_id=merchant.id,
        merchant_id=merchant.merchant_id,
        supplier_db_id=request.supplier_db_id if hasattr(request, 'supplier_db_id') else None
    )
    return new_contract

# Repayment Endpoints
@app.post("/repayment/settle", response_model=RepaymentDB, summary="Record a repayment for a contract (logged-in merchant)")
async def record_repayment(
    request: RepaymentCreate,
    current_user: User = Depends(get_current_merchant_user),
    db: Session = Depends(get_db)
):
    """
    Records a repayment for a specific contract belonging to the logged-in merchant
    and updates the contract's total_repaid and status.
    """
    merchant = current_user.merchant_profile
    if not merchant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Merchant profile not found for this user.")

    contract = db.query(Contract).filter(Contract.id == request.contract_id).first()
    if not contract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contract not found.")
    
    # Authorization check: Ensure contract belongs to the current merchant
    if contract.merchant_db_id != merchant.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Contract does not belong to the current merchant.")

    if request.amount <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Repayment amount must be positive.")

    # Prevent over-repayment or repayment on settled/rejected contracts (simple MVP logic)
    if contract.status == ContractStatus.SETTLED.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Contract is already settled.")
    if contract.status == ContractStatus.REJECTED.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Contract was rejected.")
    
    # If amount repaid exceeds remaining balance, cap it (simple MVP logic)
    if contract.amount_approved and (contract.total_repaid + request.amount > contract.amount_approved):
        repayment_amount = contract.amount_approved - contract.total_repaid
        if repayment_amount <= 0: # Already fully repaid or more
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Contract already fully repaid.")
        request.amount = repayment_amount # Adjust repayment to settle exactly
    
    return crud_repayment.create_repayment(db=db, repayment=request)

# Supplier Endpoints
@app.post("/suppliers/onboard", response_model=SupplierDB, summary="Onboard a new supplier (requires login)")
async def onboard_supplier(
    supplier_data: SupplierCreate, # Renamed to avoid clash with request
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Onboards a new supplier into the Lipwa-Trust system, linking it to the logged-in user.
    - User must be logged in and not already a supplier.
    """
    if current_user.is_supplier:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is already a supplier.")
    if current_user.supplier_profile: # Additional check if profile exists but flag not set
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already has a supplier profile.")

    # Generate a unique supplier_id
    generated_supplier_id = f"SUP-{random.randint(1000, 9999)}"
    while crud_supplier.get_supplier_by_supplier_id(db, supplier_id=generated_supplier_id):
        generated_supplier_id = f"SUP-{random.randint(1000, 9999)}"

    # Create a temporary SupplierCreate object with generated supplier_id
    supplier_data_dict = supplier_data.model_dump()
    supplier_data_dict.pop('supplier_id', None)  # Remove supplier_id if it exists to avoid duplicate keyword argument
    temp_supplier_create = SupplierCreate(supplier_id=generated_supplier_id, **supplier_data_dict)

    new_supplier = crud_supplier.create_supplier(
        db=db,
        supplier=temp_supplier_create,
        user_id=current_user.id # Link to current user
    )

    # Update user's is_supplier flag
    crud_user.update_user_is_supplier(db, current_user.id, True)
    
    return new_supplier

@app.get("/supplier/me", response_model=SupplierDB, summary="Get logged-in supplier's details")
async def get_my_supplier_details(
    current_user: User = Depends(get_current_supplier_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves the details of the logged-in supplier.
    """
    supplier = current_user.supplier_profile
    if not supplier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier profile not found for this user.")
    return supplier


@app.get("/supplier/me/contracts", response_model=List[ContractDB], summary="Get all contracts for logged-in supplier")
async def get_my_supplier_contracts(
    current_user: User = Depends(get_current_supplier_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves all contracts (both active and completed) for the logged-in supplier.
    """
    supplier = current_user.supplier_profile
    if not supplier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier profile not found for this user.")
    
    contracts = crud_contract.get_contracts_by_supplier_id(db, supplier.id)
    return contracts


@app.get("/supplier/me/contracts/active", response_model=List[ContractDB], summary="Get active contracts for logged-in supplier")
async def get_my_supplier_active_contracts(
    current_user: User = Depends(get_current_supplier_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves only active (ongoing) contracts for the logged-in supplier.
    Active means not settled or rejected.
    """
    supplier = current_user.supplier_profile
    if not supplier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier profile not found for this user.")
    
    active_contracts = crud_contract.get_active_contracts_for_supplier(db, supplier.id)
    return active_contracts


@app.get("/suppliers", response_model=List[SupplierDB], summary="Get a list of all suppliers (active user access)")
async def get_all_suppliers(
    current_user: User = Depends(get_current_active_user), # Protected endpoint
    skip: int = 0, limit: int = 100, db: Session = Depends(get_db)
):
    """
    Retrieves a list of all registered suppliers. Accessible by any active logged-in user.
    """
    suppliers = crud_supplier.get_all_suppliers(db, skip=skip, limit=limit)
    return suppliers

@app.get("/", summary="Root endpoint")
async def root():
    return {"message": "Lipwa-Trust Backend is running!"}

# To run this application:
# 1. Ensure you have created a Python virtual environment and activated it.
# 2. Install dependencies: pip install -r requirements.txt
# 3. cd backend
# 4. uvicorn main:app --reload --port 8000
