from typing import Optional
import datetime
import decimal

from sqlalchemy import Date, Index, Integer, text
from sqlalchemy.dialects.mysql import DOUBLE, TINYINT
from sqlalchemy.orm import Mapped, mapped_column

from app.db.mysql_connection import NitrosguBase


class Tabelshtat(NitrosguBase):
    __tablename__ = 'tabelshtat'
    __table_args__ = (
        Index('UK_tabelshtat', 'tutorid', 'typestr', 'dates', 'typepos', unique=True),
        Index('dates', 'dates'),
        Index('position', 'position'),
        Index('subdivisionid', 'subdivisionid'),
        Index('tutorid', 'tutorid'),
        Index('typepos', 'typepos'),
        Index('typestr', 'typestr')
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tutorid: Mapped[int] = mapped_column(Integer, nullable=False)
    typestr: Mapped[int] = mapped_column(TINYINT, nullable=False)
    dates: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    subdivisionid: Mapped[int] = mapped_column(Integer, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    rate: Mapped[decimal.Decimal] = mapped_column(DOUBLE(5, 2), nullable=False)
    typepos: Mapped[int] = mapped_column(TINYINT, nullable=False)
    curhours: Mapped[Optional[decimal.Decimal]] = mapped_column(DOUBLE(5, 2))
    realhours: Mapped[Optional[decimal.Decimal]] = mapped_column(DOUBLE(5, 2))
    maternity_leave: Mapped[Optional[int]] = mapped_column(TINYINT, server_default=text("'0'"))
