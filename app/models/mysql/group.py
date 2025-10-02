from typing import Optional
import datetime
import decimal

from sqlalchemy import Date, DateTime, Index, Integer, String, TIMESTAMP, text
from sqlalchemy.dialects.mysql import DOUBLE
from sqlalchemy.orm import Mapped, mapped_column

from app.db.mysql_connection import MySQLBase


class Group(MySQLBase):
    __tablename__ = 'groups'
    __table_args__ = (
        Index('groups_specializationID', 'specializationID'),
        Index('groups_stateID', 'stateID'),
        Index('stipenddate', 'stipenddate'),
        Index('stipstartdate', 'stipstartdate')
    )

    groupID: Mapped[int] = mapped_column(Integer, primary_key=True)
    modified: Mapped[datetime.datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))
    name: Mapped[Optional[str]] = mapped_column(String(256))
    specializationID: Mapped[Optional[int]] = mapped_column(Integer)
    stateID: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("'0'"))
    created: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    deleted: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    clerkID: Mapped[Optional[int]] = mapped_column(Integer)
    militaryID: Mapped[Optional[int]] = mapped_column(Integer)
    adviserID: Mapped[Optional[int]] = mapped_column(Integer)
    qualificationRU: Mapped[Optional[str]] = mapped_column(String(128), comment='Квалификация на рус. ОИТ 11062017')
    qualificationKZ: Mapped[Optional[str]] = mapped_column(String(128), comment='Квалификация на каз. ОИТ 11062017')
    qualificationEN: Mapped[Optional[str]] = mapped_column(String(128), comment='Квалификация на анг. ОИТ 11062017')
    stipstartdate: Mapped[Optional[datetime.date]] = mapped_column(Date)
    stipenddate: Mapped[Optional[datetime.date]] = mapped_column(Date)
    stipsize: Mapped[Optional[decimal.Decimal]] = mapped_column(DOUBLE(10, 2))
