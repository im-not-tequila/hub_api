from datetime import datetime
from pydantic import BaseModel, model_validator


class CreateCalendarEventRequest(BaseModel):
    structural_subdivision_id: int | None = None
    start_datetime: datetime
    end_datetime: datetime
    place_id: int
    title_ru: str | None = None
    title_kz: str | None = None
    title_en: str | None = None
    description_ru: str | None = None
    description_kz: str | None = None
    description_en: str | None = None
    needs_media_capture: bool
    event_type_id: int
    contacts: str | None = None
    needs_tech_support: bool | None = None

    @model_validator(mode="after")
    def fill_missing_languages(self):
        # Title: хотя бы одно поле обязательно, недостающие дублируем из первого заданного
        titles = (self.title_ru, self.title_kz, self.title_en)

        def _norm(s: str | None) -> str:
            return (s or "").strip()

        filled_titles = [_norm(t) for t in titles if _norm(t)]
        if not filled_titles:
            raise ValueError(
                "Необходимо указать название хотя бы на одном языке (title_ru, title_kz или title_en)"
            )
        first_title = filled_titles[0]
        title_ru = _norm(self.title_ru) or first_title
        title_kz = _norm(self.title_kz) or first_title
        title_en = _norm(self.title_en) or first_title

        # Description: если указано только на одном языке — дублируем в остальные
        descs = [
            _norm(self.description_ru),
            _norm(self.description_kz),
            _norm(self.description_en),
        ]
        filled_descs = [d for d in descs if d]
        first_desc = filled_descs[0] if filled_descs else None
        description_ru = _norm(self.description_ru) or first_desc
        description_kz = _norm(self.description_kz) or first_desc
        description_en = _norm(self.description_en) or first_desc

        return self.model_copy(
            update={
                "title_ru": title_ru,
                "title_kz": title_kz,
                "title_en": title_en,
                "description_ru": description_ru,
                "description_kz": description_kz,
                "description_en": description_en,
            }
        )


class UpdateCalendarEventRequest(BaseModel):
    structural_subdivision_id: int | None = None
    start_datetime: datetime | None = None
    end_datetime: datetime | None = None
    place_id: int | None = None
    title_ru: str | None = None
    title_kz: str | None = None
    title_en: str | None = None
    description_ru: str | None = None
    description_kz: str | None = None
    description_en: str | None = None
    needs_media_capture: bool | None = None
    event_type_id: int | None = None
    contacts: str | None = None
    needs_tech_support: bool | None = None

    @model_validator(mode="after")
    def fill_missing_languages(self):
        def _norm(s: str | None) -> str:
            return (s or "").strip()

        # Если передали хотя бы один title_* — заполняем остальные из первого заданного
        titles = (_norm(self.title_ru), _norm(self.title_kz), _norm(self.title_en))
        filled_titles = [t for t in titles if t]
        if filled_titles:
            first_title = filled_titles[0]
            title_ru = _norm(self.title_ru) or first_title
            title_kz = _norm(self.title_kz) or first_title
            title_en = _norm(self.title_en) or first_title
        else:
            title_ru = self.title_ru
            title_kz = self.title_kz
            title_en = self.title_en

        # Аналогично для description_* (если хотя бы одно передали)
        descs = (
            _norm(self.description_ru),
            _norm(self.description_kz),
            _norm(self.description_en),
        )
        filled_descs = [d for d in descs if d]
        if filled_descs:
            first_desc = filled_descs[0]
            description_ru = _norm(self.description_ru) or first_desc
            description_kz = _norm(self.description_kz) or first_desc
            description_en = _norm(self.description_en) or first_desc
        else:
            description_ru = self.description_ru
            description_kz = self.description_kz
            description_en = self.description_en

        return self.model_copy(
            update={
                "title_ru": title_ru,
                "title_kz": title_kz,
                "title_en": title_en,
                "description_ru": description_ru,
                "description_kz": description_kz,
                "description_en": description_en,
            }
        )


class CalendarEventResponse(BaseModel):
    id: int
    creator_user_id: int | None
    structural_subdivision_id: int | None
    start_datetime: datetime
    end_datetime: datetime
    place_id: int
    title_ru: str
    title_kz: str
    title_en: str
    description_ru: str | None
    description_kz: str | None
    description_en: str | None
    needs_media_capture: bool
    event_type_id: int
    contacts: str | None
    needs_tech_support: bool | None

    class Config:
        from_attributes = True


class CalendarEventExtendedProps(BaseModel):
    event_type: str
    place: str
    description: str | None
    needs_media: int  # 0 or 1
    needs_tech: int  # 0 or 1
    structural_subdivision: str | None
    is_owner: bool


class CalendarEventListItem(BaseModel):
    id: str  # строка для совместимости с фронтом (FullCalendar и т.п.)
    title: str
    start_datetime: datetime
    end_datetime: datetime
    extendedProps: CalendarEventExtendedProps


class EventPlaceItem(BaseModel):
    """Место проведения события (название на выбранном языке)."""
    id: int
    name: str


class EventTypeItem(BaseModel):
    """Тип события (название на выбранном языке)."""
    id: int
    name: str
