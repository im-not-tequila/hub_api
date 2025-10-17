import decimal

from sqlalchemy import Double, Index, Integer, text
from sqlalchemy.dialects.mysql import TINYINT, VARCHAR
from sqlalchemy.orm import Mapped, mapped_column

from app.db.mysql_connection import PercoBase


class Control(PercoBase):
    __tablename__ = 'controls'
    __table_args__ = (
        Index('buildingid', 'buildingid'),
        Index('inid', 'inid'),
        Index('outid', 'outid')
    )

    turniketid: Mapped[int] = mapped_column(Integer, primary_key=True)
    deviceid: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(VARCHAR(150), nullable=False)
    address: Mapped[str] = mapped_column(VARCHAR(150), nullable=False)
    inid: Mapped[int] = mapped_column(TINYINT, nullable=False)
    outid: Mapped[int] = mapped_column(TINYINT, nullable=False)
    ip: Mapped[str] = mapped_column(VARCHAR(15), nullable=False)
    buildingid: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("'0'"))
    lat: Mapped[decimal.Decimal] = mapped_column(Double(asdecimal=True), nullable=False, server_default=text("'0'"))
    lng: Mapped[decimal.Decimal] = mapped_column(Double(asdecimal=True), nullable=False, server_default=text("'0'"))

