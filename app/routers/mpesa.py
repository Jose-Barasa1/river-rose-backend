from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.models import Order

import httpx, base64, os
from datetime import datetime

router = APIRouter()  # ← no prefix here, main.py handles it

CONSUMER_KEY    = os.getenv("MPESA_CONSUMER_KEY")
CONSUMER_SECRET = os.getenv("MPESA_CONSUMER_SECRET")
SHORTCODE       = os.getenv("MPESA_SHORTCODE")
PASSKEY         = os.getenv("MPESA_PASSKEY")
CALLBACK_URL    = os.getenv("MPESA_CALLBACK_URL")


async def get_access_token() -> str:
    credentials = base64.b64encode(f"{CONSUMER_KEY}:{CONSUMER_SECRET}".encode()).decode()
    async with httpx.AsyncClient() as client:
        res = await client.get(
            "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials",
            headers={"Authorization": f"Basic {credentials}"}
        )
        data = res.json()
        if "access_token" not in data:
            raise HTTPException(status_code=401, detail=f"Token error: {data}")
        return data["access_token"]


# ── Debug route ──────────────────────────────────────────────
@router.get("/test-token")
async def test_token():
    try:
        token = await get_access_token()
        return {"success": True, "token_preview": token[:20] + "..."}
    except Exception as e:
        return {"success": False, "error": str(e)}


class STKPushRequest(BaseModel):
    phone:    str
    amount:   int
    order_id: int


@router.post("/stk-push")
async def stk_push(payload: STKPushRequest, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == payload.order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    phone = payload.phone.strip()
    if phone.startswith("+"):
        phone = phone[1:]
    if phone.startswith("0"):
        phone = "254" + phone[1:]

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    password  = base64.b64encode(f"{SHORTCODE}{PASSKEY}{timestamp}".encode()).decode()

    try:
        token = await get_access_token()
        async with httpx.AsyncClient() as client:
            res = await client.post(
                "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "BusinessShortCode": SHORTCODE,
                    "Password":          password,
                    "Timestamp":         timestamp,
                    "TransactionType":   "CustomerPayBillOnline",
                    "Amount":            payload.amount,
                    "PartyA":            phone,
                    "PartyB":            SHORTCODE,
                    "PhoneNumber":       phone,
                    "CallBackURL":       CALLBACK_URL,
                    "AccountReference":  f"RiverRose-{payload.order_id}",
                    "TransactionDesc":   f"Payment for Order #{payload.order_id}",
                }
            )
        data = res.json()
        if data.get("ResponseCode") == "0":
            order.checkout_request_id = data["CheckoutRequestID"]
            db.commit()
            return {
                "success":             True,
                "checkout_request_id": data["CheckoutRequestID"],
                "message":             "STK push sent. Check your phone."
            }
        raise HTTPException(status_code=400, detail=data.get("errorMessage", "STK push failed"))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/callback")
async def mpesa_callback(payload: dict, db: Session = Depends(get_db)):
    try:
        body   = payload["Body"]["stkCallback"]
        result = body["ResultCode"]

        if result == 0:
            items       = {i["Name"]: i["Value"] for i in body["CallbackMetadata"]["Item"]}
            mpesa_code  = items.get("MpesaReceiptNumber")
            phone       = items.get("PhoneNumber")
            account_ref = items.get("AccountReference", "")
            order_id    = int(account_ref.split("-")[-1]) if "-" in account_ref else None

            if order_id:
                order = db.query(Order).filter(Order.id == order_id).first()
                if order:
                    order.status        = "confirmed"
                    order.mpesa_code    = mpesa_code
                    order.payment_phone = str(phone)
                    db.commit()

    except Exception:
        pass

    return {"ResultCode": 0, "ResultDesc": "Success"}


@router.get("/status/{checkout_request_id}")
async def check_status(checkout_request_id: str):
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    password  = base64.b64encode(f"{SHORTCODE}{PASSKEY}{timestamp}".encode()).decode()
    try:
        token = await get_access_token()
        async with httpx.AsyncClient() as client:
            res = await client.post(
                "https://sandbox.safaricom.co.ke/mpesa/stkpushquery/v1/query",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "BusinessShortCode": SHORTCODE,
                    "Password":          password,
                    "Timestamp":         timestamp,
                    "CheckoutRequestID": checkout_request_id,
                }
            )
        data = res.json()
        return {
            "paid":    data.get("ResultCode") == "0",
            "message": data.get("ResultDesc", "Pending")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))