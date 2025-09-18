from typing import Optional
import datetime

from sqlalchemy import Index, Integer, String, TIMESTAMP, text
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import Mapped, mapped_column

from app.db.mysql_connection import MySQLBase


class StructuralSubdivision(MySQLBase):
    __tablename__ = 'structural_subdivision'
    __table_args__ = (
        Index('deleted', 'deleted'),
        Index('pos', 'pos'),
        Index('pre', 'pre')
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dean: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("'0'"))
    pre: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("'0'"))
    deleted: Mapped[int] = mapped_column(TINYINT, nullable=False, server_default=text("'0'"))
    pos: Mapped[int] = mapped_column(TINYINT, nullable=False)
    modified: Mapped[datetime.datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))
    nameru: Mapped[Optional[str]] = mapped_column(String(256))
    namekz: Mapped[Optional[str]] = mapped_column(String(256))
    nameen: Mapped[Optional[str]] = mapped_column(String(256))
    subdivision_type: Mapped[Optional[int]] = mapped_column(Integer)
    faculty_cafedra_id: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("'0'"))
    urlru: Mapped[Optional[str]] = mapped_column(String(255))
    urlkz: Mapped[Optional[str]] = mapped_column(String(255))
    urlen: Mapped[Optional[str]] = mapped_column(String(255))
    isMilitaryDepartmentMember: Mapped[Optional[int]] = mapped_column(TINYINT(1), server_default=text("'0'"))
    belong_division_id: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("'0'"))
    is_closed: Mapped[Optional[int]] = mapped_column(TINYINT(1), server_default=text("'0'"), comment='Департамент / Структурное подразделение закрыто ')
