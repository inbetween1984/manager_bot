from typing import Optional, List
from pydantic import BaseModel, HttpUrl


class Service(BaseModel):
    name: str
    price: float

class Product(BaseModel):
    name: str
    price: float
    quantity: int
    services: List[Service]

class Client(BaseModel):
    name: str
    phone: Optional[str] = None
    company: Optional[str] = None
    inn: Optional[str] = None
    orderNumber: Optional[str] = None

class Totals(BaseModel):
    products: float
    services: float
    grand: float

class Finance(BaseModel):
    accountAmount: float
    account: str

class Stock(BaseModel):
    status: str
    dealNumber: Optional[str] = None
    supplier: Optional[str] = None

class Deal(BaseModel):
    crmLink: HttpUrl
    manager: str
    clientType: str
    client: Client
    products: List[Product]
    totals: Totals
    finance: Finance
    stock: Stock
    chat_id: Optional[int] = None