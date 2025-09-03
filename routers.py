import json
from fastapi import APIRouter, Form, UploadFile, File
from handlers import save_deal_to_sheet, send_to_telegram, get_dropdown_by_name, get_column_values
from config import SPREADSHEET_ID, BOT_DATA_SPREADSHEET_ID

sales_router = APIRouter()


CREDENTIALS_FILE = "manager-bot-project-099aa7e351ba.json"

@sales_router.get("/managers")
def get_managers():
    managers = get_column_values(BOT_DATA_SPREADSHEET_ID, "Менеджеры", "A")
    return [{"name": m} for m in managers[1:]]

@sales_router.get("/accounts")
def get_accounts():
    accounts = get_column_values(BOT_DATA_SPREADSHEET_ID,"Счет", "A")
    return [{"name": a} for a in accounts[1:]]

@sales_router.get("/suppliers")
def get_suppliers():
    suppliers = get_column_values(SPREADSHEET_ID, "Справочник", "N")
    return [{"name": s} for s in suppliers[1:]]


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