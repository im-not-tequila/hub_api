from typing import Optional

from sqlalchemy import Integer
from sqlalchemy.dialects.mysql import VARCHAR
from sqlalchemy.orm import Mapped, mapped_column

from app.db.mysql_connection import PercoBase


class Status(PercoBase):
    __tablename__ = 'status'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(VARCHAR(50))

