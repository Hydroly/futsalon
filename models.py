from sqlmodel import SQLModel, Field, Relationship
from typing import List, Optional
from datetime import date

class Player(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    level: str  # "guest", "normal", "permanent"

class Session(SQLModel, table=True):  # سانس
    id: Optional[int] = Field(default=None, primary_key=True)
    date: date
    price: float
    players: str  # JSON string of player IDs, e.g., "[1,2,3]"

class Payment(SQLModel, table=True):  # تسویه
    id: Optional[int] = Field(default=None, primary_key=True)
    player_id: int = Field(foreign_key="player.id")
    amount: float
    date: date

class User(SQLModel, table=True):  # برای لاگین
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str
    password: str  # در تولید واقعی هش کن!