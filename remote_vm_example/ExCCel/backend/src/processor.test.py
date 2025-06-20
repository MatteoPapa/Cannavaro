import time
import unittest

from processor import *
from storage import save_cells, Cell


class TestFormula(unittest.TestCase):
    def test_parse(self):
        cases = [
            ('=ADD(1, 1)', ['ADD', [1, 1]]),
            ('=ADD(+1, -1)', ['ADD', [1, -1]]),
            ('=ADD(0.69, 1)', None),
            ('=ADD(0, 10e10)', None),
            ('=ADD(420, MUL(A1, 4), 69)', ['ADD', [420, ['MUL', [['A', '1'], 4]], 69]]),
            ('=ADD(A1, B1)', ['ADD', [['A', '1'], ['B', '1']]]),
            ('=ADD(A1:B10, B1)', ['ADD', [[['A', '1'], ['B', '10']], ['B', '1']]]),
            ('=CONCAT("Hello", " ", "world!", "\\"")', ['CONCAT', ['"Hello"', '" "', '"world!"', '"\\""']]),
            ('=CONCAT("\\x00", "\\x01", "\\x02")', ['CONCAT', ['"\\x00"', '"\\x01"', '"\\x02"']]),
            ('=A1:Z99', [['A', '1'], ['Z', '99']]),
            ('=A1', ['A', '1']),
        ]

        for c, cc in cases:
            try:
                f = parse_formula([], c.encode())
                self.assertListEqual(f.res.as_list()[0], cc)
            except ParsingError as e:
                if cc is not None:
                    self.fail(f'Thrown exception: {str(e)}')

    def test_compile(self):
        def store_imm(idx: int) -> bytes:
            return b'\x01' + idx.to_bytes(4, 'little')

        def store_range(sx: int, sy: int, ex: int, ey: int) -> bytes:
            return b'\x02' + bytes([sx, sy, ex, ey])

        cases = [
            ('=ADD(+1, -1)', [b'1', b'-1'], [
                Opcode(OPCODE_STORE, 1, store_imm(0)),
                Opcode(OPCODE_STORE, 1, store_imm(1)),
                Opcode(OPCODE_ADD, 2, b''),
            ]),
            ('=ADD(420, MUL(A1, 4), 69)', [b'420', b'4', b'69'], [
                Opcode(OPCODE_STORE, 1, store_imm(0)),
                Opcode(OPCODE_STORE, 1, store_range(0, 0, 0, 0)),
                Opcode(OPCODE_STORE, 1, store_imm(1)),
                Opcode(OPCODE_MUL, 2, b''),
                Opcode(OPCODE_STORE, 1, store_imm(2)),
                Opcode(OPCODE_ADD, 3, b'')
            ]),
            ('=CONCAT("Hello", " world!")', [b'Hello', b' world!'], [
                Opcode(OPCODE_STORE, 1, store_imm(0)),
                Opcode(OPCODE_STORE, 1, store_imm(1)),
                Opcode(OPCODE_CONCAT, 2, b'')
            ]),
            ('=CONCAT("\\x00", "\\x01\\x02")', [b'\x00', b'\x01\x02'], [
                Opcode(OPCODE_STORE, 1, store_imm(0)),
                Opcode(OPCODE_STORE, 1, store_imm(1)),
                Opcode(OPCODE_CONCAT, 2, b'')
            ]),
            ('=A1:Z99', [], [
                Opcode(OPCODE_STORE, 1, store_range(0, 0, 25, 98)),
            ]),
        ]

        for c, cc, ccc in cases:
            try:
                f = parse_formula([], c.encode())
                f.compile()
                self.assertListEqual(f.data, cc)
                self.assertListEqual(f.code, ccc)
            except CompilingError as e:
                if cc is not None:
                    self.fail(f'Thrown exception: {str(e)}')

    def test_evaluate(self):
        worksheet_id = os.urandom(16).hex()

        save_cells(worksheet_id, [
            Cell(0, 0, b'2', None),
        ])

        cases = [
            ('=ADD(+1, -1)', b'0'),
            ('=ADD(420, MUL(A1, 4), 69)', b'497'),
            ('=CONCAT("Hello", " world!")', b'Hello world!'),
            ('=CONCAT("\\x00", "\\x01\\x02")', b'\x00\x01\x02'),
        ]

        for c, cc in cases:
            try:
                f = parse_formula([], c.encode())
                f.compile()
                res = evaluate_formula(worksheet_id, f, str(int(time.time() * 1000)))
                self.assertEqual(res, cc)
            except EvaluationError as e:
                if cc is not None:
                    self.fail(f'Thrown exception: {str(e)}')


if __name__ == '__main__':
    unittest.main()
