from sqlalchemy.orm import Session
from db.base import Merchant
from models.merchant import MerchantCreate
from trust_score_engine import calculate_trust_score # Import trust_score_engine
import random

def get_merchant_by_merchant_id(db: Session, merchant_id: str):
    """
    Retrieves a merchant from the database by their merchant_id.
    """
    return db.query(Merchant).filter(Merchant.merchant_id == merchant_id).first()

def create_merchant(db: Session, merchant: MerchantCreate, trust_score: int, credit_limit: float, user_id: int):
    """
    Creates a new merchant record in the database, linking it to a user.
    """
    db_merchant = Merchant(
        merchant_id=merchant.merchant_id, # Use the merchant_id from the Pydantic model (generated upstream if None)
        name=merchant.name,
        business_type=merchant.business_type,
        contact_person=merchant.contact_person,
        phone_number=merchant.phone_number,
        email=merchant.email,
        avg_daily_sales=merchant.avg_daily_sales,
        consistency=merchant.consistency,
        days_active=merchant.days_active,
        trust_score=trust_score,
        credit_limit=credit_limit,
        user_id=user_id # Assign the user_id
    )
    db.add(db_merchant)
    db.commit()
    db.refresh(db_merchant)
    return db_merchant

def update_merchant_sales_and_score(db: Session, merchant: Merchant):
    """
    Simulates a day's sales for a merchant, updates their metrics,
    and recalculates their trust score and credit limit.
    """
    # Merge the merchant object into the current session to avoid session conflicts
    merchant = db.merge(merchant)
    
    # Simulate a small variation in sales and consistency
    merchant.avg_daily_sales = max(100.0, merchant.avg_daily_sales * random.uniform(0.9, 1.1))
    merchant.consistency = max(0.1, min(0.99, merchant.consistency * random.uniform(0.95, 1.05)))
    merchant.days_active += 1

    score_data = calculate_trust_score(
        merchant.avg_daily_sales,
        merchant.consistency,
        merchant.days_active
    )

    merchant.trust_score = score_data["score"]
    merchant.credit_limit = score_data["credit_limit"]

    db.add(merchant)
    db.commit()
    db.refresh(merchant)
    return merchant
