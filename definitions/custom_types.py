from typing import TypedDict

class PageItem(TypedDict):
    url: str
    title: str
    text: str


class CtxItem(TypedDict):
    doc: str
    url: str
    title: str
    section: str
    heading: str
    heading_path: str
    chunk_index: int | None
    distance: float
    overlap: int
    n_chars: int