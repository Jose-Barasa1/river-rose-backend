from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.models import Order

import httpx, base64, os
from datetime import datetime

router = APIRouter()

CONSUMER_KEY    = os.getenv("MPESA_CONSUMER_KEY")
CONSUMER_SECRET = os.getenv("MPESA_CONSUMER_SECRET")
SHORTCODE       = os.getenv("MPESA_SHORTCODE")
PASSKEY         = os.getenv("MPESA_PASSKEY")
CALLBACK_URL    = os.getenv("MPESA_CALLBACK_URL")


# ---------------------------
# TOKEN GENERATION
# ---------------------------
async def get_access_token() -> str:
    credentials = base64.b64encode(
        f"{CONSUMER_KEY}:{CONSUMER_SECRET}".encode()
    ).decode()

    async with httpx.AsyncClient(timeout=20) as client:
        res = await client.get(
            "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials",
            headers={"Authorization": f"Basic {credentials}"}
        )

    if res.status_code != 200:
        raise HTTPException(status_code=401, detail=f"Token request failed: {res.text}")

    try:
        data = res.json()
    except Exception:
        raise HTTPException(status_code=401, detail=f"Invalid token response: {res.text}")

    if "access_token" not in data:
        raise HTTPException(status_code=401, detail=f"Token error: {data}")

    return data["access_token"]


# ---------------------------
# REQUEST SCHEMA
# ---------------------------
class STKPushRequest(BaseModel):
    phone: str
    amount: int
    order_id: int


# ---------------------------
# STK PUSH
# ---------------------------
@router.post("/stk-push")
async def stk_push(payload: STKPushRequest, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == payload.order_id).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Format phone number
    phone = payload.phone.strip()
    if phone.startswith("+"):
        phone = phone[1:]
    if phone.startswith("0"):
        phone = "254" + phone[1:]

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    password  = base64.b64encode(
        f"{SHORTCODE}{PASSKEY}{timestamp}".encode()
    ).decode()

    try:
        token = await get_access_token()

        async with httpx.AsyncClient(timeout=20) as client:
            res = await client.post(
                "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "BusinessShortCode": SHORTCODE,
                    "Password": password,
                    "Timestamp": timestamp,
                    "TransactionType": "CustomerPayBillOnline",
                    "Amount": payload.amount,
                    "PartyA": phone,
                    "PartyB": SHORTCODE,
                    "PhoneNumber": phone,
                    "CallBackURL": CALLBACK_URL,
                    "AccountReference": f"RiverRose-{payload.order_id}",
                    "TransactionDesc": f"Payment for Order #{payload.order_id}",
                }
            )

        if res.status_code != 200:
            raise HTTPException(status_code=400, detail=f"STK push failed: {res.text}")

        try:
            data = res.json()
        except Exception:
            raise HTTPException(status_code=400, detail=f"Invalid STK response: {res.text}")

        if data.get("ResponseCode") == "0":
            checkout_request_id = data["CheckoutRequestID"]

            # Save checkout_request_id to DB
            order.checkout_request_id = checkout_request_id
            db.commit()

            return {
                "success": True,
                "checkout_request_id": checkout_request_id,
                "message": "STK push sent. Check your phone."
            }

        raise HTTPException(
            status_code=400,
            detail=data.get("errorMessage", "STK push failed")
        )

    except HTTPException:
        raise
    except Exception as e:
        print("STK PUSH ERROR:", str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


# ---------------------------
# CALLBACK
# ---------------------------
@router.post("/callback")
async def mpesa_callback(payload: dict, db: Session = Depends(get_db)):
    try:
        print("CALLBACK RECEIVED:", payload)

        body = payload["Body"]["stkCallback"]
        result_code = body["ResultCode"]
        checkout_request_id = body["CheckoutRequestID"]

        order = db.query(Order).filter(
            Order.checkout_request_id == checkout_request_id
        ).first()

        if not order:
            print("Order not found for checkout_request_id:", checkout_request_id)
            return {"ResultCode": 0, "ResultDesc": "Order not found"}

        if result_code == 0:
            items = {
                i["Name"]: i.get("Value")
                for i in body["CallbackMetadata"]["Item"]
            }

            order.status = "confirmed"
            order.mpesa_code = items.get("MpesaReceiptNumber")
            order.payment_phone = str(items.get("PhoneNumber"))

        else:
            order.status = "failed"

        db.commit()

    except Exception as e:
        print("CALLBACK ERROR:", str(e))
        return {"ResultCode": 0, "ResultDesc": "Handled with error"}

    return {"ResultCode": 0, "ResultDesc": "Success"}


# ---------------------------
# STATUS CHECK
# ---------------------------
@router.get("/status/{checkout_request_id}")
async def check_status(checkout_request_id: str, db: Session = Depends(get_db)):
    try:
        # ✅ FIRST: Check DB (source of truth)
        order = db.query(Order).filter(
            Order.checkout_request_id == checkout_request_id
        ).first()

        if order and order.status == "confirmed":
            return {
                "paid": True,
                "status": "confirmed",
                "message": "Payment confirmed (from DB)"
            }

        if order and order.status == "failed":
            return {
                "paid": False,
                "status": "failed",
                "message": "Payment failed (from DB)"
            }

        # If still pending → query M-Pesa
        token = await get_access_token()

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        password  = base64.b64encode(
            f"{SHORTCODE}{PASSKEY}{timestamp}".encode()
        ).decode()

        async with httpx.AsyncClient(timeout=20) as client:
            res = await client.post(
                "https://sandbox.safaricom.co.ke/mpesa/stkpushquery/v1/query",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "BusinessShortCode": SHORTCODE,
                    "Password": password,
                    "Timestamp": timestamp,
                    "CheckoutRequestID": checkout_request_id,
                }
            )

        # ✅ Handle HTTP errors
        if res.status_code != 200:
            return {
                "paid": False,
                "status": "error",
                "message": "M-Pesa API error",
                "raw": res.text
            }

        # ✅ Safe JSON parsing
        if not res.text:
            return {
                "paid": False,
                "status": "error",
                "message": "Empty response from M-Pesa"
            }

        try:
            data = res.json()
        except Exception:
            return {
                "paid": False,
                "status": "error",
                "message": "Invalid JSON from M-Pesa",
                "raw": res.text
            }

        result_code = data.get("ResultCode")

        # Still processing
        if result_code is None:
            return {
                "paid": False,
                "status": "pending",
                "message": data.get("ResultDesc", "Pending")
            }

        paid = str(result_code) == "0"

        # ✅ Update DB if confirmed
        if paid and order:
            order.status = "confirmed"
            db.commit()

        return {
            "paid": paid,
            "status": "confirmed" if paid else "failed",
            "message": data.get("ResultDesc", "Processed")
        }

    except Exception as e:
        print("STATUS ERROR:", str(e))
        raise HTTPException(status_code=500, detail="Internal server error")