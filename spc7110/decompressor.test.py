import random
import sys
import unittest
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from spc7110 import decompressor, errors


def stream(seed: int = 1, length: int = 4096) -> bytes:
    source = random.Random(seed)
    return bytes(source.randrange(256) for _ in range(length))


def started(mode: int = 0, seed: int = 1, offset: int = 0, index: int = 0) -> Any:
    found = decompressor.Decompressor(stream(seed))
    found.start(mode=mode, offset=offset, index=index)
    return found


class SourceTest(unittest.TestCase):
    def test_the_source_is_read_a_byte_at_a_time_from_the_offset(self) -> None:
        found = decompressor.Decompressor(bytes([0x11, 0x22, 0x33]))
        found.offset = 1

        self.assertEqual((found.take(), found.take()), (0x22, 0x33))

    def test_reading_past_the_end_comes_back_to_the_beginning(self) -> None:
        found = decompressor.Decompressor(bytes([0x11, 0x22]))
        found.offset = 2

        self.assertEqual(found.take(), 0x11)

    def test_an_offset_far_past_the_end_still_lands_inside(self) -> None:
        found = decompressor.Decompressor(bytes([0x11, 0x22]))
        found.offset = 9

        self.assertEqual(found.take(), 0x22)

    def test_a_source_with_nothing_in_it_is_refused(self) -> None:
        with self.assertRaises(errors.Empty):
            decompressor.Decompressor(b"")


class ModeTest(unittest.TestCase):
    def test_every_mode_the_chip_has_produces_bytes(self) -> None:
        for mode in decompressor.MODES:
            found = started(mode=mode)

            self.assertEqual(len(found.read(32)), 32)

    def test_a_mode_the_chip_does_not_have_is_refused(self) -> None:
        found = decompressor.Decompressor(stream())

        with self.assertRaises(errors.UnknownMode):
            found.start(mode=3, offset=0, index=0)

    def test_the_modes_disagree_about_the_same_stream(self) -> None:
        answers = {mode: bytes(started(mode=mode).read(64)) for mode in decompressor.MODES}

        self.assertEqual(len(set(answers.values())), len(decompressor.MODES))

    def test_the_same_stream_decodes_the_same_way_twice(self) -> None:
        self.assertEqual(started().read(128), started().read(128))

    def test_a_different_stream_decodes_differently(self) -> None:
        self.assertNotEqual(started(seed=1).read(128), started(seed=2).read(128))


class OffsetTest(unittest.TestCase):
    def test_starting_further_along_the_stream_decodes_differently(self) -> None:
        self.assertNotEqual(started(offset=0).read(64), started(offset=7).read(64))

    def test_skipping_output_is_the_same_as_reading_and_discarding(self) -> None:
        skipped = started(index=16).read(32)
        read = started(index=0)
        read.read(16)

        self.assertEqual(skipped, read.read(32))

    def test_skipping_nothing_skips_nothing(self) -> None:
        self.assertEqual(started(index=0).read(16), started().read(16))


class BufferTest(unittest.TestCase):
    def test_the_buffer_refills_when_it_empties(self) -> None:
        found = started()

        self.assertEqual(
            len(found.read(decompressor.BUFFER_BYTES * 4)), decompressor.BUFFER_BYTES * 4
        )

    def test_reading_one_byte_at_a_time_gives_the_same_answer(self) -> None:
        one = started()
        many = started()

        self.assertEqual(bytes(one.take_byte() for _ in range(64)), many.read(64))

    def test_a_decompressor_that_was_never_started_answers_nothing(self) -> None:
        found = decompressor.Decompressor(stream())

        self.assertEqual(found.take_byte(), 0x00)

    def test_the_buffer_size_is_a_power_of_two_the_chip_can_hold(self) -> None:
        self.assertEqual(decompressor.BUFFER_BYTES & (decompressor.BUFFER_BYTES - 1), 0)
        self.assertGreaterEqual(decompressor.BUFFER_BYTES, 64)


class ContextTest(unittest.TestCase):
    def test_a_fresh_start_clears_every_context(self) -> None:
        found = started()
        found.read(64)

        found.start(mode=0, offset=0, index=0)

        self.assertEqual([state.index for state in found.contexts], [0] * decompressor.CONTEXTS)

    def test_and_clears_which_symbol_each_one_thinks_is_likelier(self) -> None:
        found = started()
        found.read(64)

        found.start(mode=0, offset=0, index=0)

        self.assertEqual([state.invert for state in found.contexts], [0] * decompressor.CONTEXTS)

    def test_decoding_moves_at_least_one_context_off_its_first_row(self) -> None:
        found = started()

        found.read(256)

        self.assertTrue(any(state.index for state in found.contexts))


class ReadingTest(unittest.TestCase):
    def test_a_decompressor_prints_as_its_mode_and_where_it_is(self) -> None:
        self.assertIn("mode", repr(started()))

    def test_a_context_prints_as_its_row_and_its_flag(self) -> None:
        self.assertIn("row", repr(decompressor.Context()))


if __name__ == "__main__":
    unittest.main()
