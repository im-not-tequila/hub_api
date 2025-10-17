from typing import Optional
import datetime

from sqlalchemy import Date, Index, Integer, String, TIMESTAMP, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.mysql_connection import NitroBase


class Faculty(NitroBase):
    __tablename__ = 'faculties'
    __table_args__ = (
        Index('sapacom', 'sapacom'),
    )

    FacultyID: Mapped[int] = mapped_column(Integer, primary_key=True)
    modified: Mapped[datetime.datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), comment='Дата последнего изменения')
    sapacom: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("'0'"))
    facultyNameKZ: Mapped[Optional[str]] = mapped_column(String(128))
    facultyNameEN: Mapped[Optional[str]] = mapped_column(String(128))
    facultyNameRU: Mapped[Optional[str]] = mapped_column(String(128))
    facultyDean: Mapped[Optional[int]] = mapped_column(Integer)
    created: Mapped[Optional[datetime.date]] = mapped_column(Date)
    informationRU: Mapped[Optional[str]] = mapped_column(Text)
    informationEN: Mapped[Optional[str]] = mapped_column(Text)
    informationKZ: Mapped[Optional[str]] = mapped_column(Text)
    satellite: Mapped[Optional[int]] = mapped_column(Integer)
    proper: Mapped[Optional[int]] = mapped_column(Integer)
    dialup: Mapped[Optional[int]] = mapped_column(Integer)
    deputy_dean_academic_affairs: Mapped[Optional[int]] = mapped_column(Integer)
    rFacultyNameRU: Mapped[Optional[str]] = mapped_column(String(128))
    rFacultyNameKZ: Mapped[Optional[str]] = mapped_column(String(128))
    rFacultyNameEN: Mapped[Optional[str]] = mapped_column(String(128))
    buildingId: Mapped[Optional[int]] = mapped_column(Integer)
    auditoryId: Mapped[Optional[int]] = mapped_column(Integer)
    phone: Mapped[Optional[str]] = mapped_column(String(25))
    mail: Mapped[Optional[str]] = mapped_column(String(50))
    sites: Mapped[Optional[str]] = mapped_column(String(255))
    shortnameKZ: Mapped[Optional[str]] = mapped_column(String(128))
    shortnameRU: Mapped[Optional[str]] = mapped_column(String(128))
    shortnameEN: Mapped[Optional[str]] = mapped_column(String(128))
    oFacultyNameKZ: Mapped[Optional[str]] = mapped_column(String(255))
    oFacultyNameRU: Mapped[Optional[str]] = mapped_column(String(255))
    oFacultyNameEN: Mapped[Optional[str]] = mapped_column(String(255))
