import datetime
import uuid
from typing import Any, List, Literal, Optional

import pydantic


class TimesheetSummaryRequest(pydantic.BaseModel):
    start_date: Optional[None | datetime.date] = None
    end_date: Optional[None | datetime.date] = None

    year: Optional[None | int] = None
    week: Optional[None | int] = None
    month: Optional[None | int] = None

    segmentation: Optional[Literal['day', 'week', 'month', 'year']] = 'day'
    specific_activities: Optional[None | List[uuid.UUID]] = None
    specific_org_units: Optional[None | List[uuid.UUID]] = None
    specific_users: Optional[None | List[uuid.UUID]] = None

    only_active_users: Optional[bool] = True


class DayAndHolidayName(pydantic.BaseModel):
    week_idx: int
    week_day: str
    holiday: Optional[None | str] = None


class TimesheetCalendar(pydantic.BaseModel):
    start_date: datetime.date
    end_date: datetime.date
    week_days: List[DayAndHolidayName]


class TimesheetSummaryResponseByOrgUnits(pydantic.BaseModel):
    segmentation: Literal['day', 'week', 'month', 'year']

    year: Optional[None | int] = None
    week: Optional[None | int] = None
    month: Optional[None | int] = None
    day_in_month: Optional[None | int] = None

    calendar: TimesheetCalendar

    org_units: List[Any]
