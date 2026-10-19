import random
import sys
import unittest
from functools import partial
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import spc7110

MODE_NUMBERS = (0, 1, 2)

CONTEXT_COUNT = 32

BUFFER_BYTES = 64


def stream(seed: int = 1, length: int = 4096) -> bytes:
    source = random.Random(seed)
    return bytes(source.randrange(256) for _ in range(length))


def started(
    mode: int = 0, seed: int = 1, offset: int = 0, index: int = 0, source: bytes | None = None
) -> Any:
    given = stream(seed) if source is None else source
    return spc7110.Chip("spc7110").decompress(given, mode, offset=offset, index=index)


def held_after_one(mode: int) -> int:
    found = started(mode=mode)
    found.take_byte()
    return int(found.held)


class SourceTest(unittest.TestCase):
    def test_the_source_is_read_from_the_offset(self) -> None:
        # Arrange
        source = stream(length=256)

        # Act
        moved = started(source=source, offset=1).read(32)

        # Assert
        self.assertEqual(moved, started(source=source[1:] + source[:1]).read(32))

    def test_reading_past_the_end_comes_back_to_the_beginning(self) -> None:
        # Arrange
        source = stream(length=256)

        # Act
        wrapped = started(source=source, offset=256).read(32)

        # Assert
        self.assertEqual(wrapped, started(source=source).read(32))

    def test_an_offset_far_past_the_end_still_lands_inside(self) -> None:
        # Arrange
        source = stream(length=256)

        # Act
        far = started(source=source, offset=256 * 3 + 5).read(32)

        # Assert
        self.assertEqual(far, started(source=source, offset=5).read(32))

    def test_the_source_is_kept_as_bytes(self) -> None:
        # Arrange
        source = bytearray(stream(length=16))

        # Act
        found = spc7110.Decompressor(source)

        # Assert
        self.assertEqual((type(found.source), found.source), (bytes, bytes(source)))

    def test_a_source_with_nothing_in_it_is_refused(self) -> None:
        # Arrange
        source = b""

        # Act
        building = partial(spc7110.Decompressor, source)

        # Assert
        self.assertRaises(spc7110.Empty, building)


class ModeTest(unittest.TestCase):
    def test_every_mode_the_chip_has_produces_bytes(self) -> None:
        # Arrange
        modes = MODE_NUMBERS

        # Act
        lengths = [len(started(mode=mode).read(32)) for mode in modes]

        # Assert
        self.assertEqual(lengths, [32, 32, 32])

    def test_a_mode_the_chip_does_not_have_is_refused(self) -> None:
        # Arrange
        found = spc7110.Decompressor(stream())

        # Act
        starting = partial(found.start, 3, 0, 0)

        # Assert
        self.assertRaises(spc7110.UnknownMode, starting)

    def test_the_modes_disagree_about_the_same_stream(self) -> None:
        # Arrange
        modes = MODE_NUMBERS

        # Act
        answers = {started(mode=mode).read(64) for mode in modes}

        # Assert
        self.assertEqual(len(answers), len(modes))

    def test_the_same_stream_decodes_the_same_way_twice(self) -> None:
        # Arrange
        first = started().read(128)

        # Act
        second = started().read(128)

        # Assert
        self.assertEqual(first, second)

    def test_a_different_stream_decodes_differently(self) -> None:
        # Arrange
        first = started(seed=1).read(128)

        # Act
        second = started(seed=2).read(128)

        # Assert
        self.assertNotEqual(first, second)

    def test_a_started_decompressor_names_its_mode(self) -> None:
        # Arrange
        modes = MODE_NUMBERS

        # Act
        named = [started(mode=mode).mode for mode in modes]

        # Assert
        self.assertEqual(named, [0, 1, 2])


class OffsetTest(unittest.TestCase):
    def test_starting_further_along_the_stream_decodes_differently(self) -> None:
        # Arrange
        first = started(offset=0).read(64)

        # Act
        later = started(offset=7).read(64)

        # Assert
        self.assertNotEqual(first, later)

    def test_skipping_output_is_the_same_as_reading_and_discarding(self) -> None:
        # Arrange
        read = started(index=0)
        read.read(16)

        # Act
        skipped = started(index=16).read(32)

        # Assert
        self.assertEqual(skipped, read.read(32))

    def test_skipping_nothing_starts_at_the_first_decoded_byte(self) -> None:
        # Arrange
        source = bytes(range(256))

        # Act
        skipped = started(mode=2, source=source, index=0).read(8)

        # Assert
        self.assertEqual(skipped.hex(" "), "00 00 00 00 00 00 00 15")


class BufferTest(unittest.TestCase):
    def test_the_buffer_refills_when_it_empties(self) -> None:
        # Arrange
        found = started()
        first = found.read(BUFFER_BYTES)

        # Act
        second = found.read(BUFFER_BYTES)

        # Assert
        self.assertEqual((len(second), second == first), (BUFFER_BYTES, False))

    def test_reading_one_byte_at_a_time_gives_the_same_answer(self) -> None:
        # Arrange
        one = started()

        # Act
        taken = bytes(one.take_byte() for _ in range(64))

        # Assert
        self.assertEqual(taken, started().read(64))

    def test_a_decompressor_that_was_never_started_answers_nothing(self) -> None:
        # Arrange
        found = spc7110.Decompressor(stream())

        # Act
        taken = found.take_byte()

        # Assert
        self.assertEqual((taken, found.mode, found.held), (0x00, None, 0))

    def test_a_first_read_decodes_half_the_buffer_ahead(self) -> None:
        # Arrange
        modes = MODE_NUMBERS

        # Act
        held = [held_after_one(mode) for mode in modes]

        # Assert
        self.assertEqual(held, [BUFFER_BYTES // 2 - 1] * 3)


class ContextTest(unittest.TestCase):
    def test_a_decompressor_keeps_one_context_per_slot(self) -> None:
        # Arrange
        found = started()

        # Act
        contexts = found.contexts

        # Assert
        self.assertEqual(len(contexts), CONTEXT_COUNT)

    def test_a_fresh_start_clears_every_context(self) -> None:
        # Arrange
        found = started()
        found.read(64)

        # Act
        found.start(0, 0, 0)

        # Assert
        self.assertEqual([state.index for state in found.contexts], [0] * CONTEXT_COUNT)

    def test_and_clears_which_symbol_each_one_thinks_is_likelier(self) -> None:
        # Arrange
        found = started()
        found.read(64)

        # Act
        found.start(0, 0, 0)

        # Assert
        self.assertEqual([state.invert for state in found.contexts], [0] * CONTEXT_COUNT)

    def test_decoding_moves_at_least_one_context_off_its_first_row(self) -> None:
        # Arrange
        found = started()

        # Act
        found.read(256)

        # Assert
        self.assertNotEqual([state.index for state in found.contexts], [0] * CONTEXT_COUNT)


class ReadingTest(unittest.TestCase):
    def test_a_decompressor_prints_as_its_mode_and_where_it_is(self) -> None:
        # Arrange
        found = spc7110.Decompressor(bytes(range(256)))

        # Act
        shown = repr(found)

        # Assert
        self.assertEqual(shown, "<Decompressor mode None at 0 holding 0>")

    def test_a_context_prints_as_its_row_and_its_flag(self) -> None:
        # Arrange
        found = spc7110.Context()

        # Act
        shown = repr(found)

        # Assert
        self.assertEqual(shown, "<Context row 0 invert 0>")


def noted(asked: list[int], address: int) -> int:
    asked.append(address)
    return 0


class MappedSourceTest(unittest.TestCase):
    def test_a_decompressor_over_a_fetch_reads_what_one_over_bytes_reads(self) -> None:
        # Arrange
        source = stream(length=4096)
        mapped = spc7110.Decompressor(fetch=source.__getitem__)

        # Act
        found = [mapped.start(mode, 100, 0).read(64) for mode in MODE_NUMBERS]

        # Assert
        self.assertEqual(
            found, [started(mode, source=source, offset=100).read(64) for mode in MODE_NUMBERS]
        )

    def test_it_asks_the_fetch_for_each_address_in_turn_wrapping_at_thirty_two_bits(self) -> None:
        # Arrange
        asked: list[int] = []
        mapped = spc7110.Decompressor(fetch=partial(noted, asked))

        # Act
        mapped.start(0, 0xFFFFFFFF, 0)

        # Assert
        self.assertEqual(asked, [0xFFFFFFFF, 0x00000000])

    def test_it_needs_no_source_bytes(self) -> None:
        # Arrange
        fetch = bytes(16).__getitem__

        # Act
        mapped = spc7110.Decompressor(fetch=fetch)

        # Assert
        self.assertEqual(mapped.source, b"")


class RowTest(unittest.TestCase):
    def test_a_row_is_one_two_or_four_bytes_by_mode(self) -> None:
        # Arrange
        decoders = [started(mode) for mode in MODE_NUMBERS]

        # Act
        widths = [len(decoder.row()) for decoder in decoders]

        # Assert
        self.assertEqual(widths, [1, 2, 4])

    def test_eight_rows_hold_the_bytes_a_read_hands_out(self) -> None:
        # Arrange
        rows = started(2)

        # Act
        held = [rows.row() for _ in range(8)]

        # Assert
        self.assertEqual(
            b"".join(row[:2] for row in held) + b"".join(row[2:] for row in held),
            started(2).read(32),
        )

    def test_a_decompressor_not_yet_started_has_no_row(self) -> None:
        # Arrange
        idle = spc7110.Decompressor(bytes(16))

        # Act
        found = idle.row()

        # Assert
        self.assertEqual(found, b"")


if __name__ == "__main__":
    unittest.main()
