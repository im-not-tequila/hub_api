from typing import Optional
import datetime
import decimal

from sqlalchemy import Date, Double, Integer, String, text
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import Mapped, mapped_column

from app.db.mysql_connection import PercoBase

class Building(PercoBase):
    __tablename__ = 'buildings'

    buildingID: Mapped[int] = mapped_column(Integer, primary_key=True)
    buildingName: Mapped[Optional[str]] = mapped_column(String(256))
    address: Mapped[Optional[str]] = mapped_column(String(512))
    square: Mapped[Optional[decimal.Decimal]] = mapped_column(Double(asdecimal=True))
    usefull: Mapped[Optional[int]] = mapped_column(Integer)
    auditory: Mapped[Optional[int]] = mapped_column(Integer)
    service: Mapped[Optional[int]] = mapped_column(Integer)
    outofauditory: Mapped[Optional[int]] = mapped_column(Integer)
    finishdate: Mapped[Optional[datetime.date]] = mapped_column(Date)
    startdate: Mapped[Optional[datetime.date]] = mapped_column(Date)
    is_academic: Mapped[Optional[int]] = mapped_column(TINYINT(1), server_default=text("'1'"))
    buildingNameKz: Mapped[Optional[str]] = mapped_column(String(256))
    buildingNameEn: Mapped[Optional[str]] = mapped_column(String(256))
    addressKz: Mapped[Optional[str]] = mapped_column(String(256))
    addressEn: Mapped[Optional[str]] = mapped_column(String(256))
    lat: Mapped[Optional[str]] = mapped_column(String(25))
    lon: Mapped[Optional[str]] = mapped_column(String(25))
    floorcount: Mapped[Optional[int]] = mapped_column(Integer)
    educBuildingID: Mapped[Optional[int]] = mapped_column(Integer, comment='educationbuildings -> educBuildingID')
    useAuditoryLocation: Mapped[Optional[int]] = mapped_column(TINYINT(1), server_default=text("'0'"), comment='Указать местоположение корпуса по карте')
    latitude: Mapped[Optional[decimal.Decimal]] = mapped_column(Double(asdecimal=True), server_default=text("'0'"), comment='позиция на карте')
    longitude: Mapped[Optional[decimal.Decimal]] = mapped_column(Double(asdecimal=True), server_default=text("'0'"), comment='позиция на карте')
