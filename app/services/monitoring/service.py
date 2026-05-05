from __future__ import annotations

from app.services.monitoring.base import MonitoringServiceBase
from app.services.monitoring.employees import MonitoringEmployeesMixin
from app.services.monitoring.punctuality import MonitoringPunctualityMixin
from app.services.monitoring.schedules import MonitoringSchedulesMixin


class MonitoringService(
    MonitoringEmployeesMixin,
    MonitoringPunctualityMixin,
    MonitoringSchedulesMixin,
    MonitoringServiceBase,
):
    pass
