

from typing import Iterable, Sequence, Type, TypeVar, List
from sqlalchemy.orm import Query

paginate_T = TypeVar('T')
def paginate_data(query: Query[paginate_T], limit: int, offset: int):
    total=query.count()
    new_data = query.offset(offset).limit(limit).all()
    new_end = offset + limit if offset + limit < total else None
    return new_data, new_end, total
