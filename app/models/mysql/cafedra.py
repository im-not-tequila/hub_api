from typing import Optional
import datetime

from sqlalchemy import Date, Index, Integer, String, TIMESTAMP, Text, text
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.mysql_connection import MySQLBase


class Cafedra(MySQLBase):
    __tablename__ = 'cafedras'
    __table_args__ = (
        Index('practmanager', 'practmanager'),
    )

    cafedraID: Mapped[int] = mapped_column(Integer, primary_key=True)
    practmanager: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("'0'"))
    modified: Mapped[datetime.datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))
    cafedraNameRU: Mapped[Optional[str]] = mapped_column(String(128))
    cafedraNameKZ: Mapped[Optional[str]] = mapped_column(String(128))
    cafedraNameEN: Mapped[Optional[str]] = mapped_column(String(128))
    FacultyID: Mapped[Optional[int]] = mapped_column(Integer)
    created: Mapped[Optional[datetime.date]] = mapped_column(Date)
    cafedraManager: Mapped[Optional[int]] = mapped_column(Integer)
    informationRU: Mapped[Optional[str]] = mapped_column(Text)
    informationEN: Mapped[Optional[str]] = mapped_column(Text)
    informationKZ: Mapped[Optional[str]] = mapped_column(Text)
    buildingId: Mapped[Optional[int]] = mapped_column(Integer)
    auditoryId: Mapped[Optional[int]] = mapped_column(Integer)
    phone: Mapped[Optional[str]] = mapped_column(String(25))
    mail: Mapped[Optional[str]] = mapped_column(String(50))
    sites: Mapped[Optional[str]] = mapped_column(String(255))
    shortnameKZ: Mapped[Optional[str]] = mapped_column(String(128))
    shortnameRU: Mapped[Optional[str]] = mapped_column(String(128))
    shortnameEN: Mapped[Optional[str]] = mapped_column(String(128))
    used: Mapped[Optional[int]] = mapped_column(TINYINT(1), server_default=text("'1'"))

    tutor_cafedra: Mapped[list['TutorCafedra']] = relationship('TutorCafedra', back_populates='cafedras')
