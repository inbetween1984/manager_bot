import json
import logging
import gspread
import requests
from fastapi import UploadFile
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from schemas import Deal
from config import BOT_TOKEN, SPREADSHEET_ID

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
CREDS = Credentials.from_service_account_file("manager-bot-project-099aa7e351ba.json", scopes=SCOPES)
gc = gspread.authorize(CREDS)

def get_sheets_service():
    return build("sheets", "v4", credentials=CREDS)


def get_dropdown_by_name(sheet_name: str, row_idx: int, col_idx: int):
    service = get_sheets_service()

    sheet_metadata = service.spreadsheets().get(
        spreadsheetId=SPREADSHEET_ID,
        fields="sheets(properties(title),data(rowData(values(dataValidation))))"
    ).execute()

    for sheet in sheet_metadata['sheets']:
        if sheet['properties']['title'] == sheet_name:
            row_data = sheet['data'][0].get('rowData', [])
            if len(row_data) > row_idx and 'values' in row_data[row_idx]:
                cell_data = row_data[row_idx]['values'][col_idx]
                data_validation = cell_data.get('dataValidation')

                if data_validation and 'condition' in data_validation:
                    return [v['userEnteredValue'] for v in data_validation['condition']['values']]

    return []

def save_deal_to_sheet(data: dict):
    try:
        deal = Deal(**data)

        sh = gc.open_by_key(SPREADSHEET_ID)
        ws = sh.worksheet("Склад")

        all_rows = ws.get_all_values()
        data_rows = all_rows[1:]

        product_parts = [f"{p.name} - {p.quantity}" for p in deal.products]
        product_cell = " ".join(product_parts)
        status_product = "Заказать" if deal.stock.status == "Нет" else ""
        status_sale = "Резерв" if deal.clientType in ("ФЛ", "ЮЛ") else "Отсрочка оплаты"

        is_update = deal.stock.status == "Есть" and hasattr(deal.stock, 'dealNumber') and deal.stock.dealNumber

        if is_update:
            target_deal = str(deal.stock.dealNumber)
            for i, row in enumerate(data_rows):
                if row[0] == target_deal:
                    next_row = i + 2
                    break
            else:
                raise ValueError(f"Deal number {target_deal} not found")
            deal_num_str = target_deal
        else:
            last_filled_index = -1
            last_deal_num = 0
            for i, row in enumerate(data_rows):
                if row and len(row) > 2 and row[2].strip():
                    last_filled_index = i
                    if row[0].isdigit():
                        last_deal_num = int(row[0])
            next_row = 2 + last_filled_index + 1 if last_filled_index >= 0 else 2

            if next_row <= len(all_rows) and all_rows[next_row - 1][0].isdigit():
                deal_num_str = all_rows[next_row - 1][0]
            else:
                deal_num_str = str(last_deal_num + 1)

        row = [
            deal_num_str, "", product_cell, "", "", "", status_product, status_sale,
            deal.manager, deal.totals.products, "", "", "", "", "", "", "",
            "", deal.clientType, deal.client.name, deal.client.phone or ""
        ]

        ws.update([row], f"A{next_row}:U{next_row}")

        return {"status": "ok", "row": next_row}

    except Exception as e:
        logging.error(f"Ошибка записи в таблицу: {e}")
        return {"status": "error", "message": str(e)}


def get_column_values(sheet_id: str, sheet_name: str, column: str = "A"):
    service = get_sheets_service()
    range_name = f"{sheet_name}!{column}:{column}"

    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=sheet_id, range=range_name)
        .execute()
    )

    values = result.get("values", [])
    return [row[0] for row in values if row]


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
        total_product_sum = product.price * product.quantity
        lines.append(f"\nТовар {i}: {product.name}")
        lines.append(f"Количество: {product.quantity}")
        lines.append(f"Цена за единицу: {product.price}")
        lines.append(f"Сумма за товар: {total_product_sum}")

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
        logging.info(f"Successfully sent to Telegram chat {chat_id}")
    except requests.RequestException as e:
        error_message = f"Failed to send to Telegram: HTTP {response.status_code}, Response: {response.text}"
        logging.error(error_message)
        raise Exception(error_message)
