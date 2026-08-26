"""Finding the decompression directory in a cartridge, and what it establishes."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from conformance import cartridges


def _entry(mode: int, address: int) -> bytes:
    return bytes((mode, address >> 16, (address >> 8) & 0xFF, address & 0xFF))


def _a_data_rom(entries: list[tuple[int, int]], base: int = 8, size: int = 0x100000) -> bytearray:
    held = bytearray(size)
    at = base
    for mode, address in entries:
        held[at : at + 4] = _entry(mode, address)
        at += 4
    return held


class DirectoryTest(unittest.TestCase):
    def test_entries_come_back_as_a_mode_and_an_address(self) -> None:
        drom = _a_data_rom([(2, 0x1000), (0, 0x2000)])

        self.assertEqual(cartridges.directory(bytes(drom), 8)[0], [(2, 0x1000), (0, 0x2000)])

    def test_it_stops_where_the_addresses_stop_ascending(self) -> None:
        drom = _a_data_rom([(2, 0x2000), (2, 0x1000)])

        self.assertEqual(len(cartridges.directory(bytes(drom), 8)[0]), 1)

    def test_it_stops_at_a_mode_the_part_does_not_have(self) -> None:
        drom = _a_data_rom([(2, 0x1000), (7, 0x2000)])

        self.assertEqual(len(cartridges.directory(bytes(drom), 8)[0]), 1)

    def test_it_stops_at_an_address_past_the_end(self) -> None:
        drom = _a_data_rom([(2, 0x1000), (2, 0x200000)])

        self.assertEqual(len(cartridges.directory(bytes(drom), 8)[0]), 1)

    def test_it_reports_where_the_directory_ended(self) -> None:
        drom = _a_data_rom([(2, 0x1000), (0, 0x2000)])

        self.assertEqual(cartridges.directory(bytes(drom), 8)[1], 8 + 8)

    def test_a_base_past_the_end_yields_nothing(self) -> None:
        self.assertEqual(cartridges.directory(bytes(16), 0x1000)[0], [])


class BaseTest(unittest.TestCase):
    def test_three_immediate_loads_give_the_base(self) -> None:
        image = bytearray(b"\xea" * 0x10000)
        image[0x100:0x115] = bytes(
            (
                0xA9,
                0x08,
                0x8D,
                0x01,
                0x48,
                0xA9,
                0x00,
                0x8D,
                0x02,
                0x48,
                0xA9,
                0x00,
                0x8D,
                0x03,
                0x48,
                0xEA,
                0xEA,
                0xEA,
                0xEA,
                0xEA,
                0xEA,
            )
        )

        self.assertEqual(cartridges.bases(bytes(image)), [(0x000008, "three immediate loads")])

    def test_a_long_load_gives_the_base_from_three_bytes_of_the_image(self) -> None:
        image = bytearray(b"\xea" * 0x10000)
        image[0x2000:0x2003] = bytes((0x13, 0xA6, 0x0A))
        image[0x100:0x107] = bytes((0xAF, 0x00, 0x20, 0xC0, 0x8D, 0x01, 0x48))

        self.assertEqual(cartridges.bases(bytes(image)), [(0x0AA613, "a long load from 0x002000")])

    def test_a_long_indexed_load_is_read_the_same_way(self) -> None:
        image = bytearray(b"\xea" * 0x10000)
        image[0x2634:0x2637] = bytes((0x08, 0x00, 0x00))
        image[0x100:0x107] = bytes((0xBF, 0x34, 0x26, 0xC0, 0x8D, 0x01, 0x48))

        self.assertEqual(cartridges.bases(bytes(image))[0][0], 0x000008)

    def test_a_store_with_no_load_in_front_of_it_gives_nothing(self) -> None:
        image = bytearray(b"\xea" * 0x10000)
        image[0x100:0x103] = bytes((0x8D, 0x01, 0x48))

        self.assertEqual(cartridges.bases(bytes(image)), [])

    def test_an_image_that_never_writes_the_register_gives_nothing(self) -> None:
        self.assertEqual(cartridges.bases(b"\xea" * 0x10000), [])

    def test_an_immediate_load_not_followed_by_two_more_gives_nothing(self) -> None:
        image = bytearray(b"\xea" * 0x10000)
        image[0x100:0x105] = bytes((0xA9, 0x08, 0x8D, 0x01, 0x48))

        self.assertEqual(cartridges.bases(bytes(image)), [])

    def test_a_long_load_naming_an_address_past_the_end_gives_nothing(self) -> None:
        image = bytearray(b"\xea" * 0x1000)
        image[0x100:0x107] = bytes((0xAF, 0xFE, 0x0F, 0xC0, 0x8D, 0x01, 0x48))

        self.assertEqual(cartridges.bases(bytes(image)), [])

    def test_the_same_base_named_twice_is_reported_once(self) -> None:
        one = bytes(
            (
                0xA9,
                0x08,
                0x8D,
                0x01,
                0x48,
                0xA9,
                0x00,
                0x8D,
                0x02,
                0x48,
                0xA9,
                0x00,
                0x8D,
                0x03,
                0x48,
            )
        )
        image = bytearray(b"\xea" * 0x10000)
        image[0x100 : 0x100 + len(one)] = one
        image[0x400 : 0x400 + len(one)] = one

        self.assertEqual(len(cartridges.bases(bytes(image))), 1)

    def test_a_store_reaching_a_different_register_is_passed_over(self) -> None:
        image = bytearray(b"\xea" * 0x10000)
        image[0x100:0x105] = bytes((0xA9, 0x08, 0x8D, 0x04, 0x48))

        self.assertEqual(cartridges.bases(bytes(image)), [])


class SplitTest(unittest.TestCase):
    def test_the_program_rom_is_the_first_megabyte(self) -> None:
        self.assertEqual(cartridges.PROGRAM_BYTES, 0x100000)

    def test_the_data_rom_is_what_follows_it(self) -> None:
        image = b"\x11" * 0x100000 + b"\x22" * 0x40000

        self.assertEqual(set(cartridges.data_rom(image)), {0x22})

    def test_an_image_smaller_than_the_program_rom_has_no_data_rom(self) -> None:
        self.assertEqual(cartridges.data_rom(b"\x11" * 0x1000), b"")


class CensusTest(unittest.TestCase):
    def test_it_counts_the_streams_and_groups_them_by_mode(self) -> None:
        found = cartridges.census([(2, 0x1000), (2, 0x2000), (0, 0x3000)], 8, 0x18)

        self.assertEqual((found["streams"], found["modes"]), (3, {"0": 1, "2": 2}))

    def test_it_says_where_the_directory_sat(self) -> None:
        found = cartridges.census([(2, 0x1000)], 8, 0x0C)

        self.assertEqual(found["directory"], ["0x8", "0xc"])

    def test_it_notes_when_the_first_stream_begins_where_the_directory_ends(self) -> None:
        found = cartridges.census([(2, 0x0C)], 8, 0x0C)

        self.assertTrue(found["adjacent"])

    def test_and_when_it_does_not(self) -> None:
        found = cartridges.census([(2, 0x1000)], 8, 0x0C)

        self.assertFalse(found["adjacent"])

    def test_it_carries_no_address_of_any_stream(self) -> None:
        found = cartridges.census([(2, 0xABCDE)], 8, 0x0C)

        self.assertNotIn("abcde", json.dumps(found).lower())


class SeparationTest(unittest.TestCase):
    def test_a_run_of_one_byte_has_no_entropy(self) -> None:
        self.assertEqual(cartridges.entropy(b"\x00" * 64), 0.0)

    def test_a_run_of_every_byte_has_all_of_it(self) -> None:
        self.assertEqual(cartridges.entropy(bytes(range(256))), 8.0)

    def test_the_directory_streams_are_measured_against_random_offsets(self) -> None:
        drom = _a_data_rom([(2, 0x1000)])

        found = cartridges.separation(bytes(drom), [(2, 0x1000)], tries=4)

        self.assertEqual(sorted(found), ["noise", "real", "tried"])


class FoundInTest(unittest.TestCase):
    def test_a_cartridge_whose_code_names_a_base_yields_its_streams(self) -> None:
        image = bytearray(b"\xea" * 0x100000) + _a_data_rom([(2, 0x1000)] * 10)
        image[0x100:0x115] = bytes(
            (
                0xA9,
                0x08,
                0x8D,
                0x01,
                0x48,
                0xA9,
                0x00,
                0x8D,
                0x02,
                0x48,
                0xA9,
                0x00,
                0x8D,
                0x03,
                0x48,
                0xEA,
                0xEA,
                0xEA,
                0xEA,
                0xEA,
                0xEA,
            )
        )

        found = cartridges.found_in(bytes(image))

        assert found is not None
        self.assertEqual((found[1], found[3]), (8, "three immediate loads"))

    def test_a_base_yielding_too_few_entries_is_not_believed(self) -> None:
        image = bytearray(b"\xea" * 0x100000) + _a_data_rom([(2, 0x1000)] * 2)
        image[0x100:0x115] = bytes(
            (
                0xA9,
                0x08,
                0x8D,
                0x01,
                0x48,
                0xA9,
                0x00,
                0x8D,
                0x02,
                0x48,
                0xA9,
                0x00,
                0x8D,
                0x03,
                0x48,
                0xEA,
                0xEA,
                0xEA,
                0xEA,
                0xEA,
                0xEA,
            )
        )

        self.assertIsNone(cartridges.found_in(bytes(image)))

    def test_an_image_with_no_data_rom_yields_nothing(self) -> None:
        self.assertIsNone(cartridges.found_in(b"\xea" * 0x1000))


class ReadOneTest(unittest.TestCase):
    def test_a_cartridge_yields_a_census_with_its_separation(self) -> None:
        image = bytearray(b"\xea" * 0x100000) + _a_data_rom([(2, 0x1000)] * 10)
        image[0x100:0x10F] = bytes(
            (
                0xA9,
                0x08,
                0x8D,
                0x01,
                0x48,
                0xA9,
                0x00,
                0x8D,
                0x02,
                0x48,
                0xA9,
                0x00,
                0x8D,
                0x03,
                0x48,
            )
        )

        found = cartridges.read_one(bytes(image))

        self.assertEqual((found["streams"], found["baseFrom"]), (10, "three immediate loads"))

    def test_a_cartridge_naming_no_base_yields_nothing(self) -> None:
        self.assertIsNone(cartridges.read_one(b"\xea" * 0x200000))


class EntropyTest(unittest.TestCase):
    def test_nothing_at_all_carries_no_entropy(self) -> None:
        self.assertEqual(cartridges.entropy(b""), 0.0)


class RecordedTest(unittest.TestCase):
    def test_all_three_cartridges_were_read(self) -> None:
        found = cartridges.recorded()

        self.assertEqual(len(found["readFrom"]), 3)

    def test_every_one_of_them_separates_from_its_noise_floor(self) -> None:
        found = cartridges.recorded()

        for one in found["readFrom"]:
            self.assertLess(one["separation"]["real"], one["separation"]["noise"] - 2)

    def test_between_them_they_reach_all_three_modes(self) -> None:
        found = cartridges.recorded()

        reached = {mode for one in found["readFrom"] for mode in one["modes"]}

        self.assertEqual(sorted(reached), ["0", "1", "2"])

    def test_every_cartridge_carries_four_digests(self) -> None:
        found = cartridges.recorded()

        for one in found["readFrom"]:
            self.assertEqual(
                [key for key in ("crc32", "md5", "sha1", "sha256") if key in one],
                ["crc32", "md5", "sha1", "sha256"],
            )

    def test_a_reading_that_is_not_there_reads_as_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as where:
            self.assertEqual(cartridges.recorded(Path(where) / "absent.json"), {})


class MainTest(unittest.TestCase):
    def test_with_no_arguments_it_says_how_to_use_it(self) -> None:
        said: list[str] = []

        code = cartridges.main([], say=said.append)

        self.assertEqual((code, "usage" in said[0]), (2, True))

    def test_a_directory_that_is_not_one_is_refused(self) -> None:
        said: list[str] = []

        code = cartridges.main(["/nowhere-at-all", "/tmp"], say=said.append)

        self.assertEqual((code, any("no such" in one for one in said)), (2, True))

    def test_a_directory_holding_no_cartridge_reports_that(self) -> None:
        said: list[str] = []
        with tempfile.TemporaryDirectory() as where:
            code = cartridges.main([where, where], say=said.append)

        self.assertEqual((code, any("no cartridge" in one for one in said)), (2, True))

    def test_a_cartridge_whose_code_names_no_base_is_passed_over(self) -> None:
        said: list[str] = []
        with tempfile.TemporaryDirectory() as where:
            (Path(where) / "one.sfc").write_bytes(b"\xea" * 0x200000)

            code = cartridges.main([where, where], say=said.append)

        self.assertEqual((code, any("no cartridge" in one for one in said)), (2, True))

    def test_a_cartridge_it_can_read_is_recorded(self) -> None:
        said: list[str] = []
        image = bytearray(b"\xea" * 0x100000) + _a_data_rom([(2, 0x1000)] * 10)
        image[0x100:0x10F] = bytes(
            (
                0xA9,
                0x08,
                0x8D,
                0x01,
                0x48,
                0xA9,
                0x00,
                0x8D,
                0x02,
                0x48,
                0xA9,
                0x00,
                0x8D,
                0x03,
                0x48,
            )
        )
        with tempfile.TemporaryDirectory() as where:
            (Path(where) / "notes.txt").write_bytes(b"not a cartridge")
            (Path(where) / "one.sfc").write_bytes(bytes(image))

            code = cartridges.main([where, where], say=said.append)

            written = json.loads((Path(where) / cartridges.RECORDED).read_text())

        self.assertEqual((code, written["streams"]), (0, 10))


if __name__ == "__main__":
    unittest.main()
