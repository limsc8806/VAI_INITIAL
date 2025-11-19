from __future__ import annotations

from typing import List, Tuple, Optional, Dict
from pydantic import BaseModel, Field

BBox = Tuple[float, float, float, float]  # x0,y0,x1,y1


class PageBlock(BaseModel):
    page_no: int
    type: str  # "text" | "table" | "figure"
    bbox: BBox
    text: Optional[str] = None
    meta: Dict = Field(default_factory=dict)


class TableCell(BaseModel):
    row: int
    col: int
    text: str
    rowspan: int = 1
    colspan: int = 1


class TableStruct(BaseModel):
    page_no: int
    bbox: BBox
    cells: List[TableCell]
    n_rows: int
    n_cols: int
    csv_path: Optional[str] = None
    caption: Optional[str] = None
    id: Optional[str] = None


class FigureAsset(BaseModel):
    page_no: int
    bbox: BBox
    image_path: str
    caption: Optional[str] = None
    id: Optional[str] = None


class Chunk(BaseModel):
    type: str  # "text" | "table" | "figure"
    id: Optional[str]
    source: Dict  # {"pdf":str,"page":int,"bbox":BBox}
    payload: Dict  # text | {"csv":...} | {"image":..., "caption":...}
