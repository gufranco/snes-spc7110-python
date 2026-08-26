"""Driving both implementations with the streams real cartridges carry."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from conformance import against_cartridges as against


def _entry(mode: int, address: int) -> bytes:
    return bytes((mode, address >> 16, (address >> 8) & 0xFF, address & 0xFF))


def _a_cartridge(entries: list[tuple[int, int]]) -> bytes:
    program = bytearray(b"\xea" * 0x100000)
    program[0x100:0x10F] = bytes(
        (0xA9, 0x08, 0x8D, 0x01, 0x48, 0xA9, 0x00, 0x8D, 0x02, 0x48, 0xA9, 0x00, 0x8D, 0x03, 0x48)
    )
    data = bytearray(0x100000)
    at = 8
    for mode, address in entries:
        data[at : at + 4] = _entry(mode, address)
        at += 4
    return bytes(program + data)


class CaseTest(unittest.TestCase):
    def test_a_stream_becomes_a_case_starting_at_its_own_beginning(self) -> None:
        case = against.case_for(b"\x00" * 0x9000, 2, 0x1000)

        self.assertEqual((case.mode, case.offset, case.index), (2, 0, 0))

    def test_the_window_starts_where_the_stream_does(self) -> None:
        drom = bytes(0x1000) + b"\x5a" + bytes(0x9000)

        case = against.case_for(drom, 2, 0x1000)

        self.assertEqual(case.data[0], 0x5A)

    def test_the_window_is_bounded_so_a_whole_data_rom_is_not_handed_over(self) -> None:
        case = against.case_for(b"\x00" * 0x400000, 0, 0)

        self.assertEqual(len(case.data), against.WINDOW_BYTES)

    def test_a_stream_near_the_end_gets_what_is_left(self) -> None:
        case = against.case_for(b"\x00" * 0x100, 0, 0x80)

        self.assertEqual(len(case.data), 0x80)


class StreamTest(unittest.TestCase):
    def test_a_cartridge_yields_the_streams_its_directory_names(self) -> None:
        found = against.streams_of(_a_cartridge([(2, 0x2000)] * 10))

        self.assertEqual(len(found), 10)

    def test_a_cartridge_naming_no_base_yields_nothing(self) -> None:
        self.assertEqual(against.streams_of(b"\xea" * 0x200000), [])


class RunTest(unittest.TestCase):
    def test_a_reference_that_agrees_leaves_nothing_disagreeing(self) -> None:
        found = against.compare(
            _a_cartridge([(2, 0x2000)] * 10), ask=lambda case, driver: against.replay(case)
        )

        self.assertEqual((found["streams"], found["disagreed"]), (10, 0))

    def test_a_reference_that_differs_is_reported(self) -> None:
        found = against.compare(
            _a_cartridge([(2, 0x2000)] * 10), ask=lambda case, driver: [0xFF] * case.wanted
        )

        self.assertEqual(found["disagreed"], 10)

    def test_the_first_disagreement_is_named_with_both_answers(self) -> None:
        found = against.compare(
            _a_cartridge([(2, 0x2000)] * 10), ask=lambda case, driver: [0xFF] * case.wanted
        )

        self.assertEqual(found["first"]["reference"], 0xFF)

    def test_a_run_that_agrees_names_no_first_disagreement(self) -> None:
        found = against.compare(
            _a_cartridge([(2, 0x2000)] * 10), ask=lambda case, driver: against.replay(case)
        )

        self.assertIsNone(found["first"])

    def test_it_counts_the_bytes_it_compared(self) -> None:
        found = against.compare(
            _a_cartridge([(2, 0x2000)] * 10), ask=lambda case, driver: against.replay(case)
        )

        self.assertEqual(found["bytes"], 10 * against.WANTED_BYTES)


class RecordedTest(unittest.TestCase):
    def test_every_stream_of_every_cartridge_agreed(self) -> None:
        found = against.recorded()

        self.assertEqual(found["disagreed"], 0)

    def test_all_three_cartridges_were_driven(self) -> None:
        found = against.recorded()

        self.assertEqual(len(found["readFrom"]), 3)

    def test_more_real_streams_were_driven_than_generated_ones_exist(self) -> None:
        found = against.recorded()

        self.assertGreater(found["streams"], 200)

    def test_it_names_the_reference_commit_it_was_run_against(self) -> None:
        found = against.recorded()

        self.assertEqual(len(found["reference"]["commit"]), 40)

    def test_a_reading_that_is_not_there_reads_as_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as where:
            self.assertEqual(against.recorded(Path(where) / "absent.json"), {})


class MainTest(unittest.TestCase):
    def test_with_no_arguments_it_says_how_to_use_it(self) -> None:
        said: list[str] = []

        code = against.main([], say=said.append)

        self.assertEqual((code, "usage" in said[0]), (2, True))

    def test_a_directory_that_is_not_one_is_refused(self) -> None:
        said: list[str] = []

        code = against.main(["/nowhere-at-all", "/tmp"], say=said.append)

        self.assertEqual((code, any("no such" in one for one in said)), (2, True))

    def test_a_missing_driver_is_reported_rather_than_guessed_at(self) -> None:
        said: list[str] = []
        with tempfile.TemporaryDirectory() as where:
            code = against.main([where, where, "--driver", "/nowhere/driver"], say=said.append)

        self.assertEqual((code, any("driver" in one for one in said)), (2, True))

    def test_a_driver_option_with_nothing_after_it_is_refused(self) -> None:
        said: list[str] = []

        code = against.main(["a", "b", "--driver"], say=said.append)

        self.assertEqual((code, "usage" in said[0]), (2, True))

    def test_a_file_that_names_no_directory_base_is_passed_over(self) -> None:
        said: list[str] = []
        with tempfile.TemporaryDirectory() as where:
            driver = Path(where) / "driver"
            driver.write_bytes(b"")
            (Path(where) / "other.sfc").write_bytes(b"\xea" * 0x200000)
            (Path(where) / "one.sfc").write_bytes(_a_cartridge([(2, 0x2000)] * 10))

            code = against.main(
                [where, where, "--driver", str(driver)],
                say=said.append,
                ask=lambda case, driver: against.replay(case),
            )

        self.assertEqual(code, 0)

    def test_a_directory_holding_no_cartridge_reports_that(self) -> None:
        said: list[str] = []
        with tempfile.TemporaryDirectory() as where:
            driver = Path(where) / "driver"
            driver.write_bytes(b"")

            code = against.main([where, where, "--driver", str(driver)], say=said.append)

        self.assertEqual((code, any("no cartridge" in one for one in said)), (2, True))

    def test_a_cartridge_the_reference_agrees_with_is_recorded(self) -> None:
        said: list[str] = []
        with tempfile.TemporaryDirectory() as where:
            driver = Path(where) / "driver"
            driver.write_bytes(b"")
            (Path(where) / "one.sfc").write_bytes(_a_cartridge([(2, 0x2000)] * 10))

            code = against.main(
                [where, where, "--driver", str(driver)],
                say=said.append,
                ask=lambda case, driver: against.replay(case),
            )

            self.assertEqual((code, (Path(where) / against.RECORDED).is_file()), (0, True))

    def test_a_cartridge_the_reference_differs_on_reports_failure(self) -> None:
        said: list[str] = []
        with tempfile.TemporaryDirectory() as where:
            driver = Path(where) / "driver"
            driver.write_bytes(b"")
            (Path(where) / "one.sfc").write_bytes(_a_cartridge([(2, 0x2000)] * 10))

            code = against.main(
                [where, where, "--driver", str(driver)],
                say=said.append,
                ask=lambda case, driver: [0xFF] * case.wanted,
            )

        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
