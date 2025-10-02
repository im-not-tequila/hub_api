from typing import Optional
import datetime
import decimal

from sqlalchemy import Date, Double, ForeignKeyConstraint, Index, Integer, String, TIMESTAMP, text
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.mysql_connection import MySQLBase


class TutorCafedra(MySQLBase):
    __tablename__ = 'tutor_cafedra'
    __table_args__ = (
        ForeignKeyConstraint(['cafedraid'], ['cafedras.cafedraID'], ondelete='CASCADE', onupdate='CASCADE', name='FK_cafedraid'),
        ForeignKeyConstraint(['tutorID'], ['tutors.TutorID'], ondelete='CASCADE', onupdate='CASCADE', name='FK_tutorid'),
        Index('FK_cafedraid', 'cafedraid'),
        Index('primaryEmploymentID', 'primaryEmploymentID'),
        Index('tutorid_type', 'tutorID', 'type', unique=True)
    )

    ID: Mapped[int] = mapped_column(Integer, primary_key=True)
    tutorID: Mapped[int] = mapped_column(Integer, nullable=False)
    cafedraid: Mapped[int] = mapped_column(Integer, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    type: Mapped[int] = mapped_column(Integer, nullable=False)
    modified: Mapped[datetime.datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))
    rate: Mapped[Optional[decimal.Decimal]] = mapped_column(Double(asdecimal=True))
    hourlyFund: Mapped[Optional[int]] = mapped_column(TINYINT(1), server_default=text("'0'"))
    deleted: Mapped[Optional[int]] = mapped_column(TINYINT(1), server_default=text("'0'"))
    primaryEmploymentID: Mapped[Optional[int]] = mapped_column(Integer)
    et_contract_start_date: Mapped[Optional[datetime.date]] = mapped_column(Date)
    et_contract_finish_date: Mapped[Optional[datetime.date]] = mapped_column(Date)
    et_by_agreement: Mapped[Optional[int]] = mapped_column(TINYINT(1), server_default=text("'0'"))
    del_: Mapped[Optional[int]] = mapped_column('del', TINYINT, server_default=text("'0'"))
    primaryEmploymentPositionRU: Mapped[Optional[str]] = mapped_column(String(512))
    primaryEmploymentPositionKZ: Mapped[Optional[str]] = mapped_column(String(512))
    primaryEmploymentPositionEN: Mapped[Optional[str]] = mapped_column(String(512))
    primaryEmploymentRate: Mapped[Optional[decimal.Decimal]] = mapped_column(Double(asdecimal=True))
    organizationNameRU: Mapped[Optional[str]] = mapped_column(String(512))
    organizationNameKZ: Mapped[Optional[str]] = mapped_column(String(512))
    organizationNameEN: Mapped[Optional[str]] = mapped_column(String(512))
    countDaysByLastAgreement: Mapped[Optional[int]] = mapped_column(TINYINT(1), server_default=text("'0'"))
    foreignConsultant: Mapped[Optional[int]] = mapped_column(TINYINT(1), server_default=text("'0'"))

    cafedras: Mapped['Cafedra'] = relationship('Cafedra', back_populates='tutor_cafedra')
    tutors: Mapped['Tutor'] = relationship('Tutor', back_populates='tutor_cafedra')
