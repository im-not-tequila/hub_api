from typing import Optional
import datetime
import decimal

from sqlalchemy import Index, Integer, TIMESTAMP, text
from sqlalchemy.dialects.mysql import DOUBLE, TINYINT, VARCHAR
from sqlalchemy.orm import Mapped, mapped_column

from app.db.mysql_connection import PercoBase


class Personcontrol(PercoBase):
    __tablename__ = 'personcontrols'
    __table_args__ = (
        Index('createdate', 'createdate'),
        Index('inoutdata', 'inoutdata'),
        Index('personid', 'personid'),
        Index('repl', 'repl'),
        Index('role', 'role'),
        Index('turniketid', 'turniketid'),
        Index('type', 'type')
    )

    controlid: Mapped[int] = mapped_column(Integer, primary_key=True)
    personid: Mapped[int] = mapped_column(Integer, nullable=False)
    createdate: Mapped[datetime.datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=text('CURRENT_TIMESTAMP'))
    turniketid: Mapped[int] = mapped_column(Integer, nullable=False)
    inoutdata: Mapped[str] = mapped_column(VARCHAR(25), nullable=False)
    role: Mapped[str] = mapped_column(VARCHAR(10), nullable=False)
    repl: Mapped[int] = mapped_column(TINYINT, nullable=False, server_default=text("'0'"))
    type: Mapped[Optional[str]] = mapped_column(VARCHAR(10), server_default=text("'qrCode'"))
    shir: Mapped[Optional[decimal.Decimal]] = mapped_column(DOUBLE(14, 10), server_default=text("'0.0000000000'"))
    dolg: Mapped[Optional[decimal.Decimal]] = mapped_column(DOUBLE(14, 10), server_default=text("'0.0000000000'"))
