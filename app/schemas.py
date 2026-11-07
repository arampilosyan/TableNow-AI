from datetime import date, time
from pydantic import BaseModel, Field, ConfigDict

class ReservationCreate(BaseModel):
    restaurant_id: int
    table_id: int
    customer_name: str = Field(min_length=2, max_length=120)
    customer_phone: str = Field(min_length=6, max_length=40)
    party_size: int = Field(ge=1, le=20)
    date: date
    time: time
    duration_minutes: int = Field(default=120, ge=30, le=360)

class ReservationStatusUpdate(BaseModel):
    status: str

class TableStatusUpdate(BaseModel):
    status: str

class RestaurantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    cuisine: str
    address: str
    district: str
    latitude: float
    longitude: float
    description: str
