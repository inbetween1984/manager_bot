import json
from fastapi import APIRouter, Form, UploadFile, File
from handlers import save_deal_to_sheet, send_to_telegram, get_dropdown_by_index
from config import SPREADSHEET_ID

sales_router = APIRouter()


CREDENTIALS_FILE = "manager-bot-project-099aa7e351ba.json"

@sales_router.get("/managers")
def get_managers():
    managers = get_dropdown_by_index(0, 1, 8)
    return [{"name": m} for m in managers]

@sales_router.get("/suppliers")
def get_suppliers():
    suppliers = get_dropdown_by_index(0, 1, 21)
    return [{"name": s} for s in suppliers]


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