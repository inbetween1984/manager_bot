import asyncio
import json
from fastapi import APIRouter, Depends, Form, UploadFile, File
from sqlalchemy.orm import Session
from handlers import save_deal_to_sheet, send_to_telegram
from models import Manager, Supplier, Service, Account
from db import get_db


sales_router = APIRouter()


@sales_router.get("/managers")
def get_managers(db: Session = Depends(get_db)):
    managers = db.query(Manager).all()
    return [{"name": m.name} for m in managers]

@sales_router.get("/suppliers")
def get_suppliers(db: Session = Depends(get_db)):
    suppliers = db.query(Supplier).all()
    return [{"name": s.name} for s in suppliers]

@sales_router.get("/services")
def get_services(db: Session = Depends(get_db)):
    services = db.query(Service).all()
    return [{"name": s.name} for s in services]

@sales_router.get("/accounts")
def get_accounts(db: Session = Depends(get_db)):
    accounts = db.query(Account).all()
    return [{"name": a.name} for a in accounts]

@sales_router.post("/submit")
async def submit_sale(
    sale: str = Form(...),
    calculator: UploadFile = File(...),
    paymentFile: UploadFile = File(...),
):
    data = json.loads(sale)

    await send_to_telegram(data, calculator, paymentFile)

    save_deal_to_sheet(data)


    return {"status": "ok"}