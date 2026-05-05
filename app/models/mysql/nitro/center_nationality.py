from typing import Optional
import datetime

from sqlalchemy import Integer, String, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from app.db.mysql_connection import NitroBase


class CenterNationality(NitroBase):
    __tablename__ = 'center_nationalities'

    Id: Mapped[int] = mapped_column(Integer, primary_key=True)
    NameKZ: Mapped[Optional[str]] = mapped_column(String(128))
    NameRU: Mapped[Optional[str]] = mapped_column(String(128))
    NameEN: Mapped[Optional[str]] = mapped_column(String(128))
    update_date: Mapped[Optional[datetime.datetime]] = mapped_column(TIMESTAMP, comment='invisible')

