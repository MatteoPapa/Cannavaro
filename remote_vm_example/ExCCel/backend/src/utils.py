import json
import re
from typing import Any, Optional

from flask import Response


def cell_str_to_xy(cell: str) -> Optional[tuple[int, int]]:
    m = re.match(r'^([A-Z]+)([0-9]+)$', cell)
    if not m:
        return None

    return cell_to_xy([m[0], m[1]])


def cell_to_xy(cell: list[str]) -> Optional[tuple[int, int]]:
    assert len(cell) == 2

    alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

    # transform column name to 0-based coordinate
    x = 0
    for c in cell[0]:
        x = x * len(alphabet) + (alphabet.index(c) + 1)
    x -= 1

    # transform row number to 0-based coordinate
    y = int(cell[1]) - 1
    if y < 0:
        return None

    return x, y


def make_json_response(data: Any) -> Response:
    return Response(
        json.dumps(data),
        headers={'Content-Type': 'application/json'},
        status=200
    )


def make_error_response(code: int, error: str) -> Response:
    return Response(
        json.dumps({'error': True, 'errorMessage': error}),
        headers={'Content-Type': 'application/json'},
        status=code
    )
