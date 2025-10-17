from typing import Optional
import datetime

from sqlalchemy import Date, Integer, String
from sqlalchemy.dialects.mysql import FLOAT
from sqlalchemy.orm import Mapped, mapped_column

from app.db.mysql_connection import PercoBase


class Persontabel(PercoBase):
    __tablename__ = 'persontabel'

    tabelid: Mapped[int] = mapped_column(Integer, primary_key=True)
    personid: Mapped[Optional[int]] = mapped_column(Integer)
    iin: Mapped[Optional[str]] = mapped_column(String(12))
    hoursum: Mapped[Optional[float]] = mapped_column(FLOAT(5, 2))
    curdate: Mapped[Optional[datetime.date]] = mapped_column(Date)
    keyid: Mapped[Optional[int]] = mapped_column(Integer)
    type: Mapped[Optional[str]] = mapped_column(String(10))
    ID_podrazd: Mapped[Optional[int]] = mapped_column(Integer)
    