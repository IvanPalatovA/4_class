import uuid
from datetime import datetime
from functools import lru_cache
from typing import Literal, Annotated

from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

app = FastAPI(
    title="Учет очереди за кофем",
    description="Сервис принимает новые заказы, меняет их поля, возвращает и удаляет",
    version="1.0",
)



class Settings(BaseSettings):
    app_name = "API кофейня"
    default_offset = 0
    default_limit = 10
    hello_phrase = "Hello World!"
    model_config = SettingsConfigDict(env_file=".env")


@lru_cache
def get_settings() -> Settings:
    return Settings()

SettingsDep = Annotated["Settings", Depends(get_settings)]

class DrinkRequest(BaseModel):
    name: str = Field(
        min_length=1, description="Имя напитка", examples=["Latte", "cappucсino"]
    )
    size: Literal["small", "medium", "large"] = Field(
        description="Размер напитка", examples=["small", "medium", "large"]
    )
    count: int = Field(gt=0, description="Кол-во в одном заказе", examples=[3, 1, 10])
    name_client: str | None = Field(
        default=None, description="Имя клиента", examples=["Даша", "Настя"]
    )


class DrinkUpdate(BaseModel):
    name: str | None = Field(
        min_length=1,
        default=None,
        description="Имя напитка",
        examples=["Latte", "cappucсino"],
    )
    size: Literal["small", "medium", "large"] | None = Field(
        default=None,
        description="Размер напитка",
        examples=["small", "medium", "large"],
    )
    status: Literal["pending", "ready", "completed"] | None = Field(
        default=None,
        description="Текущий статус заказа",
        examples=["pending", "ready", "completed"],
    )
    count: int | None = Field(
        default=None, gt=0, description="Кол-во в одном заказе", examples=[3, 1, 10]
    )
    name_client: str | None = Field(
        default=None, description="Имя клиента", examples=["Даша", "Настя"]
    )


class DrinkFull(DrinkRequest):
    id: uuid.UUID = Field(
        default_factory=lambda: uuid.uuid4(),
        description="Уникальный идентификатор заказа",
        examples=[
            "bd338a50-ec3b-4242-9a13-5608b59ade30",
            "8dd80a65-06fb-4815-835d-962df8dc609d",
        ],
    )
    status: Literal["pending", "ready", "completed"] = Field(
        default="pending",
        description="Текущий статус заказа",
        examples=["pending", "ready", "completed"],
    )
    time: str = Field(
        default_factory=lambda: datetime.now().strftime("%H:%M"),
        description="Время создания заказа",
        examples=["23:10", "11:43"],
    )


orders: dict[uuid.UUID, DrinkFull] = {}


class GetInfoClass(BaseModel):
    service: str = Field(
        min_length=1,
        description="Название сервиса",
        examples=["Coffe APi", "coffe апи"],
    )
    count: int = Field(gt=-1, description="Кол-во активных заказов", examples=[32, 0])


class GetHello(BaseModel):
    service: str = Field(
        default="Hello world!",
        min_length=1,
        description="Проверка сервиса",
        examples=["Привет мир!", "Здравствуй, мир!"],
    )


@app.get(
    "/",
    response_model=GetHello,
    tags=["Сервисы"],
    summary="Приветственное сообщение сервера",
)
async def get_start(settings: SettingsDep):
    return GetHello(service=settings.hello_phrase)


@app.get(
    "/info",
    response_model=GetInfoClass,
    tags=["Сервисы"],
    summary="Краткая инфомрация о сервисе",
)
async def get_info(settings: Settings):
    return GetInfoClass(service=settings.app_name, count=len(orders))


@app.post("/orders", status_code=201, tags=["Заказы"], summary="Создать новый заказ")
async def create_drink(drink: DrinkRequest):
    full = DrinkFull(**drink.model_dump())
    orders[full.id] = full
    return full


@app.get("/orders", tags=["Заказы"], summary="Получить заказы")
async def order_drink(
    settings: Settings,
    status_filter: None | Literal["pending", "ready"] = None,
    limit: int | None = Query(default=None, gt=0),
    offset: int | None = Query(default=None, gt=0)):
    limit = settings.default_limit if limit is None else limit
    offset = settings.default_offset if offset is None else offset
    result = []
    if status_filter is not None:
        result = [order for order in orders.values() if order.status == status_filter]
    else:
        result = list(orders.values())
    if limit < 0:
        return result[offset:]
    return result[offset : offset + limit]


@app.get(
    "/orders/{id}",
    response_model=DrinkFull,
    tags=["Заказы"],
    summary="Получить конкретный заказ по id",
)
async def get_order(id: uuid.UUID):
    result: DrinkFull | None = orders.get(id, None)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Заказ с номером {id} не найден")
    return result


@app.patch(
    "/orders/{id}",
    response_model=DrinkFull,
    tags=["Заказы"],
    summary="Изменить определенные поля у заказы с номер id",
)
async def patch_orders(id: uuid.UUID, update_model: DrinkUpdate):
    obj = orders.get(id, None)
    if obj is None:
        raise HTTPException(status_code=404, detail=f"Заказ с номером {id} не найден")

    orders[id] = obj.model_copy(update=update_model.model_dump(exclude_unset=True))
    return orders[id]


@app.delete(
    "/orders/{id}",
    status_code=204,
    tags=["Заказы"],
    summary="Удалить заказ с номером id",
)
async def delete_drink(id: uuid.UUID):
    order = orders.get(id, None)
    if order is None:
        raise HTTPException(status_code=404, detail=f"Заказ с номером {id} не найден")
    del orders[id]
