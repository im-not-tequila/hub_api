import datetime
import decimal

from sqlalchemy import Index, Integer, TIMESTAMP, Time, text
from sqlalchemy.dialects.mysql import DOUBLE, TINYINT
from sqlalchemy.orm import Mapped, mapped_column

from app.db.mysql_connection import NitrosguBase


class TutorStructuralsubdivision(NitrosguBase):
    __tablename__ = 'tutor_structuralsubdivision'

    __table_args__ = (
        Index('IDX_tutor_structuralsubdivision_TutorID', 'TutorID'),
        Index('IDX_tutor_structuralsubdivision_deleted', 'deleted'),
        Index('IDX_tutor_structuralsubdivision_position', 'position'),
        Index('IDX_tutor_structuralsubdivision_subdivisionid', 'subdivisionid'),
        Index('IDX_tutor_structuralsubdivision_type', 'type'),
        Index('IDX_tutor_structuralsubdivision_worktime', 'worktime')
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    TutorID: Mapped[int] = mapped_column(Integer, nullable=False)
    subdivisionid: Mapped[int] = mapped_column(Integer, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    rate: Mapped[decimal.Decimal] = mapped_column(DOUBLE(4, 2), nullable=False)
    type: Mapped[int] = mapped_column(TINYINT, nullable=False)
    deleted: Mapped[int] = mapped_column(TINYINT, nullable=False, server_default=text("'0'"))
    modified: Mapped[datetime.datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))
    worktime: Mapped[datetime.time] = mapped_column(Time, nullable=False, server_default=text("'08:00:00'"))
