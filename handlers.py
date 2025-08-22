import json
import logging
import gspread
import requests
from fastapi import UploadFile
from google.oauth2.service_account import Credentials
from schemas import Deal
from config import BOT_TOKEN, SPREADSHEET_ID

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
CREDS = Credentials.from_service_account_file("manager-bot-project-099aa7e351ba.json", scopes=SCOPES)
gc = gspread.authorize(CREDS)


def save_deal_to_sheet(data: dict):
   try:
        deal = Deal(**data)

        sh = gc.open_by_key(SPREADSHEET_ID)
        ws = sh.sheet1

        product_names = [p.name for p in deal.products]
        product_cell = f"{len(product_names)} шт.; " + "; ".join(product_names)
        status_product = "заказать" if deal.stock.status == "Нет" else ""
        status_sale = "Резерв" if deal.clientType in ("ФЛ", "ЮЛ") else "Отсрочка платежа"

        row = [
            "", "", product_cell, "", "", "", status_product, status_sale,
            deal.manager, deal.totals.products, "", "", "", "", "", "", "",
            "", deal.clientType, deal.client.name, deal.client.phone or ""
        ]
        next_row = len(ws.get_all_values()) + 1
        ws.append_row(row, table_range=f"A{next_row}:U{next_row}")

        return {"status": "ok", "row": next_row}

   except Exception as e:
       logging.error(f"Ошибка записи в таблицу: {e}")
       return {"status": "error", "message": str(e)}


def format_deal_message(data: dict) -> str:
    deal = Deal(**data)

    lines = [f"Менеджер: {deal.manager}", f"Тип клиента: {deal.clientType}"]

    client_info = [f"Имя: {deal.client.name}"]
    if deal.client.phone:
        client_info.append(f"Телефон: {deal.client.phone}")
    if deal.client.inn:
        client_info.append(f"ИНН: {deal.client.inn}")
    if deal.client.company:
        client_info.append(f"Компания: {deal.client.company}")
    if deal.client.orderNumber:
        client_info.append(f"Номер заказа: {deal.client.orderNumber}")
    lines.append("Клиент:\n" + "\n".join(client_info))

    for i, product in enumerate(deal.products, start=1):
        lines.append(f"\nТовар {i}: {product.name}")
        lines.append(f"Сумма за товар: {product.price}")

        if product.services:
            lines.append("Доп. услуги:")
            for s in product.services:
                lines.append(f"- {s.name} - {s.price}")
            total_services = sum(s.price for s in product.services)
            lines.append(f"Сумма за доп. услуги: {total_services}")

    lines.append(f"\nОбщая сумма сделки: {deal.totals.grand}")
    lines.append(f"Сумма поступившая на счет: {deal.finance.accountAmount} ({deal.finance.account})")

    if deal.stock.status == "Нет":
        lines.append(f"Склад: нет, заказать у {deal.stock.supplier}")
    else:
        lines.append(f"Склад: есть, номер сделки {deal.stock.dealNumber}")

    return "\n".join(lines)


async def send_to_telegram(data: dict, calculator: UploadFile, paymentFile: UploadFile):
    message = format_deal_message(data)
    deal = Deal(**data)
    chat_id = deal.chat_id

    media = [
        {
            "type": "photo",
            "media": "attach://calculator",
            "caption": message,
        },
        {
            "type": "photo",
            "media": "attach://paymentFile"
        }
    ]
    files = {
        "calculator": (calculator.filename, await calculator.read(), calculator.content_type),
        "paymentFile": (paymentFile.filename, await paymentFile.read(), paymentFile.content_type)
    }

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMediaGroup"
    payload = {"chat_id": chat_id, "media": json.dumps(media)}
    try:
        response = requests.post(url, data=payload, files=files)
        response.raise_for_status()
    except requests.RequestException as e:
        raise e
