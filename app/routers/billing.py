"""
Cheapest working shape for subscriptions: Stripe Checkout (hosted page,
so you never handle card numbers yourself) plus one webhook that flips
is_subscribed on when payment succeeds.

Setup on Stripe's dashboard:
1. Create a Product with a recurring monthly Price -> copy its ID into
   STRIPE_PRICE_ID.
2. Get your secret key from /apikeys -> STRIPE_SECRET_KEY.
3. Add a webhook endpoint pointing at
   https://your-backend-url/billing/webhook, listening for
   checkout.session.completed -> copy its signing secret into
   STRIPE_WEBHOOK_SECRET.
"""

import datetime
import stripe
from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.auth import get_current_user
from app.models.db_models import User

router = APIRouter(prefix="/billing", tags=["billing"])
stripe.api_key = settings.stripe_secret_key


@router.post("/checkout")
def create_checkout_session(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    if not user.stripe_customer_id:
        customer = stripe.Customer.create(email=user.email, name=user.name)
        user.stripe_customer_id = customer.id
        db.commit()

    session = stripe.checkout.Session.create(
        customer=user.stripe_customer_id,
        mode="subscription",
        line_items=[{"price": settings.stripe_price_id, "quantity": 1}],
        success_url=settings.frontend_url + "?subscribed=true",
        cancel_url=settings.frontend_url + "?subscribed=false",
        metadata={"user_id": str(user.id)},
    )
    return {"checkout_url": session.url}


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, settings.stripe_webhook_secret)
    except (ValueError, stripe.error.SignatureVerificationError):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = session.get("metadata", {}).get("user_id")
        if user_id:
            user = db.query(User).filter(User.id == int(user_id)).first()
            if user:
                user.is_subscribed = True
                subscription_id = session.get("subscription")
                if subscription_id:
                    try:
                        sub = stripe.Subscription.retrieve(subscription_id)
                        if sub.get("current_period_end"):
                            user.subscription_expires_at = datetime.datetime.fromtimestamp(sub["current_period_end"], datetime.timezone.utc).replace(tzinfo=None)
                    except Exception:
                        pass
                db.commit()

    if event["type"] in ("customer.subscription.deleted", "invoice.payment_failed"):
        customer_id = event["data"]["object"].get("customer")
        user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
        if user:
            user.is_subscribed = False
            db.commit()

    return {"received": True}


@router.get("/status")
def subscription_status(user: User = Depends(get_current_user)):
    active = bool(user.is_subscribed and (not user.subscription_expires_at or user.subscription_expires_at > datetime.datetime.utcnow()))
    return {"is_subscribed": active, "expires_at": user.subscription_expires_at}
