from typing import Any, Dict, List, Literal, Optional
import datetime

import pydantic
import tortoise.timezone


class UniversalTableGetRequest(pydantic.BaseModel):
    profile: Optional[None | str] = None
    response_format: Optional[Literal['table', 'objects', 'key-value']] = 'objects'

    key_value_response_format_key: Optional[None | str] = None

    # header: Optional[bool] = True
    only_data: Optional[bool] = False
    meta: Optional[bool] = True
    fields: Optional[List[str] | str] = None  # None is all Ω
    # dict_filters: Optional[Dict[str, str]] = None
    filters: Optional[None | str] = None
    json_filters: Optional[None | str] = None

    #TODO: ukinuti

    v3_filters: Optional[None | Any] = None

    search: Optional[None | str] = None

    v3f_statuses: Optional[None | str] = None
    v3f_priorities: Optional[None | str] = None
    v3f_service_groups: Optional[None | str] = None  # ?
    v3f_departments: Optional[None | str] = None
    v3f_assigned_to: Optional[None | str] = None
    v3f_customers: Optional[None | str] = None
    v3f_types: Optional[None | str] = None
    v3f_sites: Optional[None | str] = None
    v3f_created_by: Optional[None | str] = None
    v3f_last_updated_by: Optional[None | str] = None

    order_by: Optional[str] = None
    page: Optional[int] = 1
    per_page: Optional[int] = 100

    default_timezone_for_naive_datetime: Optional[None|str] = 'Europe/Belgrade'


class Column(pydantic.BaseModel):
    field: str
    name: str
    widths: Optional[List[int] | None] = None
    sortable: Optional[bool] = False
    filterable: Optional[bool | Dict] = False
    type: Optional[str] = 'string'
    lov: Optional[str] = None
    display_name: Optional[str] = None
    align_text: Optional[Literal['start', 'end', 'center']] = 'start'
    color: Optional[str] = None
    # mapping: Optional[Any] = None


class Summary(pydantic.BaseModel):
    count: int

    page: int
    per_page: int
    total_pages: int


class Header(pydantic.BaseModel):
    additional: Optional[Dict[str, Any]] = None
    websockets: Optional[Any] = None
    columns: List[Column]
    summary: Summary
    response_format: Literal['table', 'objects', 'key-value'] = 'objects'
    # response_format: Optional[Literal['table', 'objects']] = 'objects'


class UniversalTableResponse(pydantic.BaseModel):
    header: Header
    data: List


class UniversalTableResponseBaseSchema(pydantic.BaseModel):
    @classmethod
    def build(cls, model_item, item_schema, request: UniversalTableGetRequest) -> Dict[str, Any] | List[Any]:
        model_loc = item_schema.model_loc()

        def _process_if_time(field: str):
            nonlocal model_item
            _value = eval(f'model_item.{model_loc[field]}')
            is_datetime = isinstance(_value, datetime.datetime)
            if is_datetime:
                if tortoise.timezone.is_aware(_value):
                    # _value = tortoise.timezone.make_naive(_value, timezone='Europe/Belgrade')
                    _value = tortoise.timezone.make_naive(_value, timezone=request.default_timezone_for_naive_datetime)
                _value = str(_value)

            return _value

        if request.response_format == 'objects':
            res = {}
            for field in cls.order():
                try:
                    res[field] = _process_if_time(field)
                except Exception as e:
                    raise
        elif request.response_format == 'key-value':
            res = {}
            for field in cls.order():
                res[field] = _process_if_time(field)

        elif request.response_format == 'table':
            res = []
            for field in cls.order():
                res.append(_process_if_time(field))
        else:
            raise NameError(f"Unknown response_format: {request.response_format}")

        return res

    @classmethod
    def header(cls, request: UniversalTableGetRequest, summary: Summary, response_format: Literal['objects', 'table', 'key-value'] = 'objects'):

        res = Header(columns=[], summary=summary, response_format=response_format,
                     websockets=cls.websockets())

        widths = cls.column2width()
        justify = cls.column2justify()
        titles = cls.column2title()
        mapping = cls.column2mapping()

        for field in cls.order():
            try:
                type_ = cls.model_fields[field].annotation.__name__

                column = Column(
                    name=field,
                    field=field,
                    type=cls.column_data_type(field) or type_,
                    sortable=cls.sortable(field),
                    filterable=cls.filter_properties(field),
                    widths=widths[field] if field in widths else None,
                    align_text=justify[field] if field in justify else 'start',
                    display_name=titles[field],
                    mapping=mapping[field] if field in mapping else None
                )
                res.columns.append(column)
            except Exception as e:
                raise

        return res
