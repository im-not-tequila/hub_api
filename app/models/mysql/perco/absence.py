from typing import Optional
import datetime

from sqlalchemy import Date, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.mysql_connection import PercoBase


class Absence(PercoBase):
    __tablename__ = 'absence'

    num: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[str] = mapped_column(String(10), primary_key=True)
    ID: Mapped[Optional[int]] = mapped_column(Integer)
    IIN: Mapped[Optional[str]] = mapped_column(String(12))
    FIO: Mapped[Optional[str]] = mapped_column(String(255))
    Data1: Mapped[Optional[datetime.date]] = mapped_column(Date)
    Data2: Mapped[Optional[datetime.date]] = mapped_column(Date)

