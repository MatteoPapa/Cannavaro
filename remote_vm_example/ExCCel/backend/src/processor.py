import os
import socket
import string
from ast import literal_eval
from dataclasses import dataclass
from typing import Optional, Union

import pyparsing as pp
from bitstring import pack, BitStream, ConstBitStream
from pyparsing import ParseException, ParseResults
from typing_extensions import ReadOnly

from storage import Cell
from utils import cell_to_xy


class CompilingError(Exception):
    def __init__(self, msg: str):
        super().__init__(msg)


# Numeric opcodes
OPCODE_STORE: ReadOnly[int] = 0x0
OPCODE_ADD: ReadOnly[int] = 0x1
OPCODE_SUB: ReadOnly[int] = 0x2
OPCODE_MUL: ReadOnly[int] = 0x3
OPCODE_DIV: ReadOnly[int] = 0x4
OPCODE_AND: ReadOnly[int] = 0x5
OPCODE_OR: ReadOnly[int] = 0x6
OPCODE_XOR: ReadOnly[int] = 0x7
OPCODE_ABS: ReadOnly[int] = 0x8
OPCODE_COUNTA: ReadOnly[int] = 0x9
OPCODE_MIN: ReadOnly[int] = 0xa
OPCODE_MAX: ReadOnly[int] = 0xb
OPCODE_AVG: ReadOnly[int] = 0xc

# String opcodes
OPCODE_LEN: ReadOnly[int] = 0xd
OPCODE_CONCAT: ReadOnly[int] = 0xe
OPCODE_JOIN: ReadOnly[int] = 0xf
OPCODE_TRIM: ReadOnly[int] = 0x10
OPCODE_LOWER: ReadOnly[int] = 0x11
OPCODE_UPPER: ReadOnly[int] = 0x12


@dataclass
class Opcode:
    opcode: int
    params: int
    extra: bytes

    @staticmethod
    def store_imm(data_idx: int) -> 'Opcode':
        return Opcode(OPCODE_STORE, 1, pack('uintle:8, uintle:32', 1, data_idx).tobytes())

    @staticmethod
    def store_range(start_x: int, start_y: int, end_x: int, end_y: int) -> 'Opcode':
        return Opcode(OPCODE_STORE, 1, pack(
            'uintle:8, uintle:8, uintle:8, uintle:8, uintle:8', 2, start_x, start_y, end_x, end_y,
        ).tobytes())


FORMULA_FUNC_TO_OPCODE = {
    'ADD': lambda n: Opcode(OPCODE_ADD, n, b''),
    'SUB': lambda n: Opcode(OPCODE_SUB, n, b''),
    'MUL': lambda n: Opcode(OPCODE_MUL, n, b''),
    'DIV': lambda n: Opcode(OPCODE_DIV, n, b''),
    'AND': lambda n: Opcode(OPCODE_AND, n, b''),
    'OR': lambda n: Opcode(OPCODE_OR, n, b''),
    'XOR': lambda n: Opcode(OPCODE_XOR, n, b''),
    'ABS': lambda n: Opcode(OPCODE_ABS, n, b''),
    'COUNTA': lambda n: Opcode(OPCODE_COUNTA, n, b''),
    'MIN': lambda n: Opcode(OPCODE_MIN, n, b''),
    'MAX': lambda n: Opcode(OPCODE_MAX, n, b''),
    'AVG': lambda n: Opcode(OPCODE_AVG, n, b''),
    'LEN': lambda n: Opcode(OPCODE_LEN, n, b''),
    'CONCAT': lambda n: Opcode(OPCODE_CONCAT, n, b''),
    'JOIN': lambda n: Opcode(OPCODE_JOIN, n, b''),
    'TRIM': lambda n: Opcode(OPCODE_TRIM, n, b''),
    'LOWER': lambda n: Opcode(OPCODE_LOWER, n, b''),
    'UPPER': lambda n: Opcode(OPCODE_UPPER, n, b'')
}


class Formula:
    res: ParseResults
    code: list[Opcode]
    data: list[bytes]

    def __init__(self, cells: list[Cell], res: ParseResults):
        self.res = res
        self.cells = cells
        self.code = []
        self.data = []

    def __str__(self):
        res, = self.res.as_list()
        return str(res)

    def _get_cell(self, x: int, y: int) -> bytes:
        for cell in self.cells:
            if cell.x == x and cell.y == y:
                return cell.content

        return b''

    def compile(self) -> None:
        res, = self.res.as_list()
        self._compile(res)

    def _compile(self, instr: Union[list, int, str]) -> None:
        if (isinstance(instr, str) and instr[0] == '"' and instr[-1] == '"') or isinstance(instr, int):
            data = instr if isinstance(instr, str) else f'"{instr}"'
            data = literal_eval('b' + data)
            assert isinstance(data, bytes)
            if data not in self.data:
                self.data.append(data)

            self.code.append(Opcode.store_imm(self.data.index(data)))
        elif isinstance(instr, list) and isinstance(instr[0], str) and all(isinstance(x, list) for x in instr[1:]):
            for el in instr[1]:
                self._compile(el)

            if len(instr[1]) > 8:
                raise CompilingError('Too many params in function call')

            f = FORMULA_FUNC_TO_OPCODE.get(instr[0], None)
            if f is None:
                raise CompilingError(f'Unknown function: {instr[0]}')

            self.code.append(f(len(instr[1])))
        elif isinstance(instr, list) and len(instr) == 2 and isinstance(instr[0], list) and isinstance(instr[1], list):
            start, end = cell_to_xy(instr[0]), cell_to_xy(instr[1])
            if not start or start[0] < 0 or start[0] > 63 or start[1] < 0 or start[1] > 63:
                raise CompilingError(f'Invalid start cell: {instr[0]}')
            elif not end or end[0] < 0 or end[0] > 63 or end[1] < 0 or end[1] > 63:
                raise CompilingError(f'Invalid end cell: {instr[1]}')

            if self._get_cell(start[0], start[1]).startswith(b'=') or self._get_cell(end[0], end[1]).startswith(b'='):
                raise CompilingError('Cross-references in formulas are not supported')

            self.code.append(Opcode.store_range(start[0], start[1], end[0], end[1]))
        elif isinstance(instr, list) and len(instr) == 2 and isinstance(instr[0], str) and isinstance(instr[1], str):
            cell = cell_to_xy(instr)
            if not cell or cell[0] < 0 or cell[0] > 63 or cell[1] < 0 or cell[1] > 63:
                raise CompilingError(f'Invalid cell: {instr}')

            if self._get_cell(cell[0], cell[1]).startswith(b'='):
                raise CompilingError('Cross-references in formulas are not supported')

            self.code.append(Opcode.store_range(cell[0], cell[1], cell[0], cell[1]))
        else:
            raise CompilingError(f'Unknown instruction: {instr}')


class ParsingError(Exception):
    def __init__(self, msg: str):
        super().__init__(msg)


def parse_formula(cells: list[Cell], formula: bytes) -> Optional[Formula]:
    if not formula.startswith(b'='):
        return None

    eq, lpar, rpar, colon, comma = pp.Suppress.using_each("=():,")
    col_ref, row_ref = pp.Word(string.ascii_uppercase), pp.Word(pp.nums)
    cell_ref = pp.Group(col_ref + row_ref)
    cell_range = pp.Group(cell_ref + colon + cell_ref)

    expr = pp.Forward()
    func_call = pp.Group(pp.Word(string.ascii_uppercase) + pp.Group(lpar + pp.DelimitedList(expr, comma) + rpar))
    expr <<= pp.common.signed_integer | func_call | cell_range | cell_ref | pp.dbl_quoted_string

    try:
        res = (eq + expr).parse_string(formula.decode(), parse_all=True)
        return Formula(cells, res)
    except ParseException as e:
        raise ParsingError(f'There was an error parsing: {e}')


class EvaluationError(Exception):
    def __init__(self, msg: str):
        super().__init__(msg)


PROCESSOR_HOST = os.getenv('PROCESSOR_HOST', '127.0.0.1')
PROCESSOR_PORT = int(os.getenv('PROCESSOR_PORT', '1337'))


def read_bytes(sock: socket.socket, n: int) -> bytes:
    buff = bytearray(n)
    pos = 0
    while pos < n:
        cr = sock.recv_into(memoryview(buff)[pos:])
        if cr == 0:
            raise EOFError
        pos += cr
    return buff


def evaluate_formula(worksheet_id: str, formula: Formula, timestamp: str) -> bytes:
    assert len(worksheet_id) == 32
    assert len(formula.code) > 0

    # create code blob
    blob_code = BitStream()
    for c in formula.code:
        blob_code += pack('uintle:8, uintle:16', c.opcode, c.params)
        blob_code += c.extra

    # create data blob
    blob_data = BitStream()
    for d in formula.data:
        blob_data += pack(
            'uintle:8, uintle:56, bytes:64, uintle:64',
            len(d), 0, d.ljust(64, b'\x00'), 0
        )

    if len(timestamp) > 0xff:
        raise EvaluationError("timestamp str too long")

    data = BitStream()
    data += pack('bytes:32', worksheet_id.encode())
    data += pack('uintle:8', len(timestamp))
    data += pack('uintle:32', len(blob_code.tobytes()))
    data += pack('uintle:32', len(blob_data.tobytes()))
    data += timestamp.encode()
    data += blob_code
    data += blob_data

    try:
        with socket.create_connection((PROCESSOR_HOST, PROCESSOR_PORT)) as s:
            s.send(data.tobytes())

            status, res_len = ConstBitStream(read_bytes(s, 5)).unpack('uintle:8, uintle:32')
            res = read_bytes(s, res_len)

            if status != 0:
                raise EvaluationError(res.decode())

            return res
    except EOFError:
        raise EvaluationError('There was an EOF error')
    except ConnectionError as e:
        raise EvaluationError(f'There was a connection error: {e}')
