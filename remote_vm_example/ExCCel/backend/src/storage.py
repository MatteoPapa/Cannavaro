import os
from dataclasses import dataclass
from typing import Optional

from bitstring import ConstBitStream, BitStream, pack


@dataclass
class Cell:
    x: int
    y: int
    content: bytes
    evaluated: Optional[bytes]

    @staticmethod
    def contains(cells: list['Cell'], x: int, y: int) -> bool:
        for cell in cells:
            if cell.x == x and cell.y == y:
                return True
        return False

    def as_dict(self) -> dict:
        return {
            'x': self.x,
            'y': self.y,
            'content': self.content.hex(),
            'evaluated': self.evaluated.hex() if self.evaluated is not None else None
        }


WORKSHEETS_PATH = os.getenv('WORKSHEETS_PATH', '/worksheets')


def get_cells(worksheet_id: str) -> list[Cell]:
    with open(os.path.join(WORKSHEETS_PATH, worksheet_id), 'rb') as f:
        data = f.read()

    data = ConstBitStream(data)

    cells_count = data.read('uintle:16')
    cells = []
    for _ in range(cells_count):
        x, y, content_len = data.readlist('uintle:8, uintle:8, uintle:8')
        content = data.read(f'bytes:{content_len}')
        cells.append(Cell(x, y, content, None))

    return cells


def save_cells(worksheet_id: str, cells: list[Cell]):
    data = BitStream()
    data += pack('uintle:16', len(cells))

    for cell in cells:
        data += pack('uintle:8, uintle:8, uintle:8', cell.x, cell.y, len(cell.content))
        data += cell.content

    with open(os.path.join(WORKSHEETS_PATH, worksheet_id), 'wb') as f:
        f.write(data.tobytes())
