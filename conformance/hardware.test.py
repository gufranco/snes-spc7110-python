import json
import sys
import unittest
from functools import partial
from pathlib import Path
from typing import Any, override

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import spc7110

HERE = Path(__file__).resolve().parent

WORKED = bytes(range(256))


def part() -> Any:
    return spc7110.Chip("spc7110")


def held_after_one(mode: int) -> int:
    started = part().decompress(WORKED, mode)
    started.read(1)
    return int(started.held)


def first_bit(first_byte: int) -> int:
    return int(part().decompress(bytes([first_byte]) + bytes(15), 0).read(1)[0] >> 7)


def declared(name: str) -> dict[str, Any]:
    held = json.loads((HERE / name).read_text())
    assert isinstance(held, dict), f"{name} does not hold an object"
    return held


DIRECTORY = 0x000010

ROWS_PER_TILE = 8


def a_cartridge(mode: int, index: int = 0) -> bytes:
    data = bytearray(bytes(range(256)) * 256)
    entry_bytes = declared("hardware.json")["facts"]["directoryEntryBytes"]["value"]
    at = DIRECTORY + index * entry_bytes
    data[at : at + 4] = bytes((mode, 0x00, 0x20, 0x00))
    return bytes(spc7110.PROGRAM_BYTES) + bytes(data)


def started_through_registers(mode: int, index: int = 0) -> Any:
    chip = spc7110.Chip("spc7110", rom=a_cartridge(mode, index)).reset()
    chip.write(0x4801, DIRECTORY)
    chip.write(0x4802, 0x00)
    chip.write(0x4803, 0x00)
    chip.write(0x4804, index)
    chip.write(0x4806, 0x00)
    return chip


class DocumentTest(unittest.TestCase):
    @override
    def setUp(self) -> None:
        self.declared = declared("hardware.json")
        self.facts: dict[str, Any] = self.declared["facts"]

    def test_both_upper_rungs_are_recorded_as_empty(self) -> None:
        order = self.declared["authority"]["order"]

        self.assertEqual(
            ("of which there is none" in order[0], "of which there is none" in order[1]),
            (True, True),
        )

    def test_the_search_for_a_document_is_recorded_with_its_date(self) -> None:
        missing = self.declared["authority"]["whatIsMissing"]

        self.assertIn("2026-08-21", missing)

    def test_no_constant_claims_to_be_documented(self) -> None:
        claimed = [name for name, fact in self.facts.items() if fact["verified"]]

        self.assertEqual(claimed, [])

    def test_every_constant_names_its_evidence_and_what_would_settle_it(self) -> None:
        missing = [
            name
            for name, fact in self.facts.items()
            if not (fact.get("evidence") and fact.get("howToSettleIt"))
        ]

        self.assertEqual(missing, [])

    def test_what_nothing_settles_is_recorded_rather_than_filled_in(self) -> None:
        stated = self.declared["notStated"]

        self.assertGreaterEqual(len(stated), 4)


class ConstantTest(unittest.TestCase):
    @override
    def setUp(self) -> None:
        self.facts: dict[str, Any] = declared("hardware.json")["facts"]

    def test_the_three_modes_are_the_ones_declared(self) -> None:
        # Arrange
        modes = self.facts["modes"]["value"]

        # Act
        started = [part().decompress(WORKED, mode).mode for mode in modes]

        # Assert
        self.assertEqual(started, modes)

    def test_and_a_mode_past_the_declared_ones_is_refused(self) -> None:
        # Arrange
        beyond = max(self.facts["modes"]["value"]) + 1

        # Act
        starting = partial(part().decompress, WORKED, beyond)

        # Assert
        self.assertRaises(spc7110.UnknownMode, starting)

    def test_the_coder_keeps_the_declared_number_of_contexts(self) -> None:
        # Arrange
        contexts = self.facts["contexts"]["value"]

        # Act
        kept = len(part().decompress(WORKED, 0).contexts)

        # Assert
        self.assertEqual(kept, contexts)

    def test_the_buffer_is_the_declared_size(self) -> None:
        # Arrange
        buffered = self.facts["bufferBytes"]["value"]

        # Act
        held = [held_after_one(mode) for mode in self.facts["modes"]["value"]]

        # Assert
        self.assertEqual(held, [buffered // 2 - 1] * 3)

    def test_and_the_record_says_that_size_is_not_a_character_size(self) -> None:
        # Arrange
        fact = self.facts["bufferBytes"]

        # Act
        note = fact["note"]

        # Assert
        self.assertIn("coincidence rather than a derivation", note)

    def test_the_interval_starts_at_the_declared_width(self) -> None:
        # Arrange
        boundary = self.facts["spanFull"]["value"] - spc7110.tables.EVOLUTION[0][0]

        # Act
        first_bits = [first_bit(boundary), first_bit(boundary + 1)]

        # Assert
        self.assertEqual(first_bits, [0, 1])

    def test_and_renormalises_where_the_worked_example_needs(self) -> None:
        # Arrange
        started = part().decompress(WORKED, "4bpp")

        # Act
        decoded = started.read(16)

        # Assert
        self.assertEqual(
            (decoded.hex(" "), started.mode, started.offset, started.held),
            ("00 00 00 00 00 00 00 15 00 f2 00 1d 00 e2 00 19", 2, 12, 16),
        )

    def test_and_moves_context_zero_where_the_worked_example_says(self) -> None:
        # Arrange
        started = part().decompress(WORKED, "1bpp")

        # Act
        started.read(64)

        # Assert
        self.assertEqual(repr(started.contexts[0]), "<Context row 48 invert 0>")

    def test_the_threshold_is_half_the_interval(self) -> None:
        # Arrange
        span = self.facts["spanFull"]["value"]

        # Act
        threshold = self.facts["renormaliseBelow"]["value"]

        # Assert
        self.assertEqual(threshold, span >> 1)


class RegisterInterfaceTest(unittest.TestCase):
    @override
    def setUp(self) -> None:
        self.facts: dict[str, Any] = declared("hardware.json")["facts"]

    def test_the_measurement_against_ares_adds_up(self) -> None:
        # Arrange
        measured = declared("hardware.json")["authority"]["registerInterface"]

        # Act
        found = (
            measured["cartridgeBytes"] // measured["cartridgeStreams"],
            measured["registerCaseBytes"] // measured["registerCases"],
            measured["disagreed"],
        )

        # Assert
        self.assertEqual(found, (512, 256, 0))

    def test_and_the_readme_quotes_its_counts(self) -> None:
        # Arrange
        measured = declared("hardware.json")["authority"]["registerInterface"]

        # Act
        readme = (HERE.parent / "README.md").read_text()

        # Assert
        self.assertIn(
            f"{measured['cartridgeStreams']} cartridge streams and {measured['registerCases']}"
            " register-driven cases",
            readme,
        )

    def test_the_program_rom_is_the_declared_size(self) -> None:
        # Arrange
        declared_bytes = self.facts["programRomBytes"]["value"]

        # Act
        found = (spc7110.PROGRAM_BYTES, len(spc7110.Chip("spc7110").program))

        # Assert
        self.assertEqual(found, (declared_bytes, declared_bytes))

    def test_the_master_clock_is_the_declared_one(self) -> None:
        # Arrange
        declared_hz = self.facts["masterClockHz"]["value"]

        # Act
        found = spc7110.chip.MASTER_CLOCK_HZ

        # Assert
        self.assertEqual(found, declared_hz)

    def test_reset_sets_the_declared_bank_registers(self) -> None:
        # Arrange
        chip = spc7110.Chip("spc7110")

        # Act
        chip.reset()

        # Assert
        self.assertEqual(
            [chip.read(0x4830 + at) for at in range(5)], self.facts["powerOnBanks"]["value"]
        )

    def test_the_register_window_is_the_declared_one(self) -> None:
        # Arrange
        window = self.facts["registerWindow"]["value"]
        chip = spc7110.Chip("spc7110").reset()

        # Act
        answered = [answers(chip, address) for address in (window["first"], window["last"])]

        # Assert
        self.assertEqual((answered, answers(chip, window["last"] + 1)), ([True, True], False))

    def test_banks_50_and_58_alias_the_declared_registers(self) -> None:
        # Arrange
        aliases = self.facts["registerWindow"]["value"]["aliases"]
        chip = spc7110.Chip("spc7110").reset()
        chip.write(0x4809, 0x05)

        # Act
        found = (chip.read(0x50ABCD), chip.read(0x581234))

        # Assert
        self.assertEqual(
            (aliases, found, chip.read(0x4809)), ({"0x50": 0x00, "0x58": 0x08}, (0x00, 0x00), 0x04)
        )

    def test_a_start_is_ready_on_the_declared_clock_and_not_before(self) -> None:
        # Arrange
        clocks = self.facts["decompressionStartClocks"]["value"]
        chip = started_through_registers(0)

        # Act
        found = (chip.tick(clocks).read(0x480C), chip.tick(1).read(0x480C))

        # Assert
        self.assertEqual(found, (0x00, 0x80))

    def test_a_multiply_ends_on_the_declared_clock_and_not_before(self) -> None:
        # Arrange
        clocks = self.facts["multiplyClocks"]["value"]
        chip = spc7110.Chip("spc7110").reset()
        chip.write(0x4825, 0x00)

        # Act
        found = (chip.tick(clocks).read(0x482F), chip.tick(1).read(0x482F))

        # Assert
        self.assertEqual(found, (0x81, 0x01))

    def test_a_divide_ends_on_the_declared_clock_and_not_before(self) -> None:
        # Arrange
        clocks = self.facts["divideClocks"]["value"]
        chip = spc7110.Chip("spc7110").reset()
        chip.write(0x4827, 0x00)

        # Act
        found = (chip.tick(clocks).read(0x482F), chip.tick(1).read(0x482F))

        # Assert
        self.assertEqual(found, (0x80, 0x00))

    def test_the_directory_entry_is_read_at_the_declared_stride(self) -> None:
        # Arrange
        chip = started_through_registers(2, index=3)

        # Act
        found = bytes(chip.tick(21).read(0x4800) for _ in range(32))

        # Assert
        self.assertEqual(
            found,
            spc7110.Decompressor(a_cartridge(2, 3)[spc7110.PROGRAM_BYTES :])
            .start(2, 0x2000, 0)
            .read(32),
        )

    def test_a_tile_is_the_declared_size_with_the_upper_planes_last(self) -> None:
        # Arrange
        sizes = self.facts["tileBytes"]["value"]
        chips = [started_through_registers(mode).tick(21) for mode in range(3)]

        # Act
        found = [
            bytes(chip.read(0x4800) for _ in range(size))
            for chip, size in zip(chips, sizes.values(), strict=True)
        ]

        # Assert
        self.assertEqual(
            found, [tile_from_rows(mode, size) for mode, size in enumerate(sizes.values())]
        )


def answers(chip: Any, address: int) -> bool:
    try:
        chip.read(address)
    except spc7110.OutOfRange:
        return False
    return True


def tile_from_rows(mode: int, size: int) -> bytes:
    rows = spc7110.Decompressor(a_cartridge(mode)[spc7110.PROGRAM_BYTES :]).start(mode, 0x2000, 0)
    held = [rows.row() for _ in range(ROWS_PER_TILE)]
    tile = b"".join(row[:2] for row in held) + b"".join(row[2:] for row in held)
    assert len(tile) == size
    return tile


class DivergenceTest(unittest.TestCase):
    @override
    def setUp(self) -> None:
        self.entries: list[dict[str, Any]] = declared("divergences.json")["divergences"]

    def test_each_entry_says_which_source_the_package_follows(self) -> None:
        allowed = {"document", "reference", "neither"}

        self.assertEqual({entry["packageFollows"] for entry in self.entries} - allowed, set())

    def test_each_entry_says_what_would_settle_it(self) -> None:
        missing = [entry["id"] for entry in self.entries if not entry.get("wouldSettleIt")]

        self.assertEqual(missing, [])

    def test_the_absence_of_a_document_is_recorded_as_serious(self) -> None:
        entry = next(
            item for item in self.entries if item["id"] == "no-document-exists-for-this-part"
        )

        self.assertEqual(entry["severity"], "high")

    def test_agreement_with_a_reference_is_recorded_as_not_hardware(self) -> None:
        entry = next(
            item
            for item in self.entries
            if item["id"] == "agreement-with-the-reference-is-not-hardware"
        )

        self.assertIn("nothing here could tell", entry["reasoning"])

    def test_the_inviting_coincidence_is_recorded_before_anybody_cites_it(self) -> None:
        named = {entry["id"] for entry in self.entries}

        self.assertIn("the-buffer-size-is-not-a-character-size", named)


if __name__ == "__main__":
    unittest.main(verbosity=1)
