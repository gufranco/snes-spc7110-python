import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, NoReturn, override

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from spc7110 import doctor, models


class Complaint(Exception):
    pass


def a_finding(
    name: str = "something", ok: bool = True, detail: str = "detail", advice: str | None = None
) -> Any:
    return doctor.Finding(name, ok, detail, advice)


def a_pin(name: str = "snes9x", commit: str = "2971061") -> Path:
    where = Path(tempfile.mkdtemp()) / "pinned.json"
    where.write_text(json.dumps({"reference": {"name": name, "commit": commit}}))
    return where


class FindingTest(unittest.TestCase):
    def test_a_finding_says_what_was_checked(self) -> None:
        self.assertEqual(a_finding(name="the decoder").name, "the decoder")

    def test_and_whether_it_was_well(self) -> None:
        self.assertTrue(a_finding(ok=True).ok)
        self.assertFalse(a_finding(ok=False).ok)

    def test_a_healthy_finding_prints_with_a_mark_that_says_so(self) -> None:
        self.assertIn("ok", a_finding(ok=True).line)

    def test_and_an_unhealthy_one_prints_differently(self) -> None:
        self.assertNotIn("ok", a_finding(ok=False).line)

    def test_every_finding_carries_what_it_actually_saw(self) -> None:
        self.assertIn("4 bits", a_finding(detail="4 bits").line)

    def test_an_unhealthy_finding_says_what_to_do_about_it(self) -> None:
        self.assertIn("go and look", a_finding(ok=False, advice="go and look").report)

    def test_a_healthy_one_carries_no_advice(self) -> None:
        self.assertEqual(a_finding(ok=True, advice="x").report, a_finding(ok=True).line)

    def test_a_finding_prints_as_itself(self) -> None:
        self.assertIn("something", repr(a_finding()))


class ExamineTest(unittest.TestCase):
    def test_the_examination_produces_findings(self) -> None:
        self.assertTrue(doctor.examine())

    def test_it_reports_the_python_it_is_running_on(self) -> None:
        self.assertIn("python", [one.name for one in doctor.examine()])

    def test_and_the_version_of_this_package(self) -> None:
        self.assertIn("snes-spc7110-python", [one.name for one in doctor.examine()])

    def test_the_package_and_the_part_do_not_share_a_name(self) -> None:
        """Two lines with one name in a report is a line somebody misreads."""
        names = [one.name for one in doctor.examine()]

        self.assertEqual(len(names), len(set(names)))

    def test_the_part_is_reported_with_the_line_pulled(self) -> None:
        """Driven rather than described, so a part that stopped offering it shows here."""
        found = [one for one in doctor.examine() if one.name == "spc7110"]

        self.assertIn("resets and carries nothing across it", found[0].detail)

    def test_a_part_that_builds_and_will_not_reset_is_reported_as_broken(self) -> None:
        class WillNotReset(models.Chip):
            @override
            def reset(self) -> NoReturn:
                raise Complaint("the line did nothing")

        found = [
            one
            for one in doctor.examine(chip=lambda name: WillNotReset(name))
            if one.name == "spc7110"
        ]

        self.assertFalse(found[0].ok)

    def test_and_one_finding_per_mode_it_covers(self) -> None:
        from spc7110 import models

        names = [one.name for one in doctor.examine()]

        for mode in models.MODES:
            self.assertIn(mode, names, mode)

    def test_every_finding_carries_a_detail(self) -> None:
        for one in doctor.examine():
            self.assertTrue(one.detail, one.name)

    def test_a_mode_that_will_not_build_is_reported_rather_than_hidden(self) -> None:
        def boom(_name: str, _source: Any) -> Any:
            raise Complaint("the decoder exploded")

        self.assertTrue(any(not one.ok for one in doctor.examine(build=boom)))

    def test_and_the_report_carries_what_it_said_and_what_kind(self) -> None:
        def boom(_name: str, _source: Any) -> Any:
            raise Complaint("the decoder exploded")

        text = "\n".join(one.report for one in doctor.examine(build=boom))

        self.assertIn("the decoder exploded", text)
        self.assertIn("Complaint", text)

    def test_a_mode_that_builds_is_reported_with_its_depth(self) -> None:
        for one in doctor.examine():
            if one.name == "4bpp":
                self.assertIn("4 bits", one.detail)


class DeterminismTest(unittest.TestCase):
    """That the same stream gives the same bytes here as anywhere else."""

    def test_the_report_carries_what_a_known_stream_decodes_to(self) -> None:
        self.assertIn("known stream", [one.name for one in doctor.examine()])

    def test_a_decoder_that_will_not_decode_is_reported_rather_than_hidden(self) -> None:
        def boom(_name: str, _source: Any) -> Any:
            raise Complaint("nothing decodes")

        found = doctor._known(boom)

        self.assertFalse(found.ok)
        self.assertIn("nothing decodes", found.detail)

    def test_the_bytes_it_reports_are_the_bytes_it_decoded(self) -> None:
        class Counting:
            def __init__(self) -> None:
                self.given = 0

            def take_byte(self) -> int:
                self.given += 1
                return self.given

        found = doctor._known(lambda _name, _source: Counting())

        self.assertIn("01 02", found.detail)


class EmptyTest(unittest.TestCase):
    def test_a_decompressor_with_nothing_to_decompress_is_refused(self) -> None:
        for one in doctor.examine():
            if one.name == "empty stream":
                self.assertTrue(one.ok)

    def test_one_that_accepts_it_anyway_is_a_failure(self) -> None:
        found = doctor._empty(lambda _source: object())

        self.assertFalse(found.ok)

    def test_and_one_that_throws_something_else_is_reported_as_what_it_threw(self) -> None:
        def boom(_source: Any) -> Any:
            raise Complaint("wrong complaint")

        found = doctor._empty(boom)

        self.assertFalse(found.ok)
        self.assertIn("wrong complaint", found.detail)


class PinTest(unittest.TestCase):
    def test_the_reference_it_is_held_to_is_named(self) -> None:
        found = doctor.examine(pin=a_pin(name="somebody else"))

        self.assertIn("somebody else", " ".join(one.detail for one in found))

    def test_and_the_commit_it_is_pinned_to(self) -> None:
        found = doctor.examine(pin=a_pin(commit="deadbeef"))

        self.assertIn("deadbeef", " ".join(one.detail for one in found))

    def test_and_the_digest_of_the_file_that_says_so(self) -> None:
        import hashlib

        where = a_pin()

        found = doctor.examine(pin=where)

        self.assertIn(
            hashlib.sha256(where.read_bytes()).hexdigest(), " ".join(one.detail for one in found)
        )

    def test_a_pin_that_is_not_here_is_a_failure(self) -> None:
        found = doctor.examine(pin=Path("/nowhere/at/all.json"))

        self.assertTrue(any(one.name == "reference" and not one.ok for one in found))

    def test_a_pin_that_is_here_and_damaged_says_so(self) -> None:
        where = Path(tempfile.mkdtemp()) / "pinned.json"
        where.write_text("{ not json at all")

        found = doctor.examine(pin=where)

        self.assertIn("not readable as JSON", " ".join(one.detail for one in found))

    def test_a_pin_that_names_nothing_is_a_failure(self) -> None:
        where = Path(tempfile.mkdtemp()) / "pinned.json"
        where.write_text(json.dumps({}))

        found = doctor.examine(pin=where)

        self.assertTrue(any(one.name == "reference" and not one.ok for one in found))

    def test_the_pin_it_reads_by_default_is_the_one_in_this_repository(self) -> None:
        self.assertTrue(doctor.PIN.exists())


class DriverTest(unittest.TestCase):
    def test_a_driver_that_is_built_is_reported_as_here(self) -> None:
        where = Path(tempfile.mkdtemp()) / "driver"
        where.write_bytes(b"not really a driver")

        self.assertIn(
            "built and here", " ".join(one.detail for one in doctor.examine(driver=where))
        )

    def test_one_that_is_not_built_says_what_will_skip(self) -> None:
        found = doctor.examine(driver=Path("/nowhere/at/all"))

        self.assertIn("skip", " ".join(one.detail for one in found))

    def test_and_that_is_not_treated_as_a_failure(self) -> None:
        for one in doctor.examine(driver=Path("/nowhere/at/all")):
            if one.name == "reference driver":
                self.assertTrue(one.ok)


class ReportTest(unittest.TestCase):
    def test_the_report_has_a_line_for_every_finding(self) -> None:
        found = doctor.examine()

        self.assertGreaterEqual(len(doctor.report(found)), len(found))

    def test_it_opens_with_something_that_says_what_it_is(self) -> None:
        self.assertIn("spc7110", doctor.report(doctor.examine())[0])

    def test_an_unhealthy_run_says_how_many_did_not_pass(self) -> None:
        self.assertIn("1", " ".join(doctor.report([a_finding(ok=False)])))

    def test_a_healthy_run_says_there_is_nothing_to_report(self) -> None:
        self.assertIn("nothing to report", " ".join(doctor.report([a_finding(ok=True)])))


class EntryTest(unittest.TestCase):
    def test_a_healthy_run_reports_success(self) -> None:
        self.assertEqual(
            doctor.main([], examine=lambda **_: [a_finding(ok=True)], say=lambda _: None), 0
        )

    def test_an_unhealthy_one_reports_failure(self) -> None:
        self.assertEqual(
            doctor.main([], examine=lambda **_: [a_finding(ok=False)], say=lambda _: None), 1
        )

    def test_the_report_is_printed_rather_than_kept(self) -> None:
        said: list[str] = []

        doctor.main([], examine=lambda **_: [a_finding(ok=True)], say=said.append)

        self.assertTrue(said)

    def test_a_real_run_says_something_about_this_machine(self) -> None:
        said: list[str] = []

        doctor.main([], say=said.append)

        self.assertIn("spc7110", " ".join(said))


if __name__ == "__main__":
    unittest.main()
