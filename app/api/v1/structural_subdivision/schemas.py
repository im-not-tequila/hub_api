from typing import Optional

from pydantic import BaseModel


class StructuralSubdivisionItem(BaseModel):
    id: int
    dean: int
    pre: int
    name: Optional[str]
    subdivision_type: Optional[int]
    faculty_cafedra_id: Optional[int]
