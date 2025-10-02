from typing import Optional
import datetime

from sqlalchemy import Integer, String, TIMESTAMP, text
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import Mapped, mapped_column

from app.db.mysql_connection import MySQLBase


class TutorPositions(MySQLBase):
    __tablename__ = 'tutor_positions'

    ID: Mapped[int] = mapped_column(Integer, primary_key=True)
    modified: Mapped[datetime.datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))
    NameRU: Mapped[Optional[str]] = mapped_column(String(1024))
    NameKZ: Mapped[Optional[str]] = mapped_column(String(1024))
    NameEN: Mapped[Optional[str]] = mapped_column(String(1024))
    roleType: Mapped[Optional[int]] = mapped_column(Integer)
    chief_position: Mapped[Optional[int]] = mapped_column(TINYINT(1), server_default=text("'0'"))
    correspondStandardPosition: Mapped[Optional[int]] = mapped_column(Integer)
