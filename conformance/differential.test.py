import stat
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from conformance import differential

BUILT = Path(differential.DEFAULT_DRIVER)

HAS_DRIVER = BUILT.exists()


class CaseTest(unittest.TestCase):
    def test_a_run_covers_every_mode(self) -> None:
        modes = {case.mode for case in differential.cases(seeds=3)}

        self.assertEqual(modes, set(differential.MODES))

    def test_the_same_seed_produces_the_same_stream(self) -> None:
        first = differential.cases(seeds=2)
        second = differential.cases(seeds=2)

        self.assertEqual([case.data for case in first], [case.data for case in second])

    def test_different_seeds_produce_different_streams(self) -> None:
        streams = {case.data for case in differential.cases(seeds=4)}

        self.assertGreater(len(streams), 1)

    def test_a_case_starts_somewhere_in_its_own_stream(self) -> None:
        for case in differential.cases(seeds=4):
            self.assertLess(case.offset, len(case.data))

    def test_some_cases_skip_output_before_they_are_read(self) -> None:
        self.assertTrue(any(case.index for case in differential.cases(seeds=8)))

    def test_a_case_prints_as_its_mode_and_its_seed(self) -> None:
        found = repr(differential.cases(seeds=1)[0])

        self.assertIn("mode", found)


class ReplayTest(unittest.TestCase):
    def test_replaying_a_case_answers_as_many_bytes_as_it_asks_for(self) -> None:
        case = differential.cases(seeds=1)[0]

        self.assertEqual(len(differential.replay(case)), case.wanted)

    def test_the_same_case_replays_the_same_way(self) -> None:
        case = differential.cases(seeds=1)[0]

        self.assertEqual(differential.replay(case), differential.replay(case))


class ComparisonTest(unittest.TestCase):
    def test_two_identical_answers_report_nothing(self) -> None:
        self.assertIsNone(differential.disagreement([1, 2], [1, 2]))

    def test_a_byte_that_differs_is_named_with_its_position(self) -> None:
        self.assertEqual(differential.disagreement([1, 2], [1, 3]), (1, 2, 3))

    def test_an_answer_that_stops_early_is_reported(self) -> None:
        found = differential.disagreement([1, 2], [1])

        assert found is not None
        self.assertEqual(found[0], 1)


class OptionTest(unittest.TestCase):
    def test_the_defaults_are_enough(self) -> None:
        self.assertEqual(differential.options([]).seeds, differential.SEEDS)

    def test_the_number_of_seeds_can_be_set(self) -> None:
        self.assertEqual(differential.options(["--seeds", "5"]).seeds, 5)

    def test_and_the_driver(self) -> None:
        self.assertEqual(differential.options(["--driver", "here"]).driver, "here")

    def test_an_option_with_no_value_is_refused(self) -> None:
        with self.assertRaises(differential.Usage):
            differential.options(["--seeds"])

    def test_an_option_it_does_not_know_is_refused(self) -> None:
        with self.assertRaises(differential.Usage):
            differential.options(["--nonsense"])


class DriverTest(unittest.TestCase):
    def scripted(self, body: str) -> Path:
        where = Path(tempfile.mkdtemp()) / "fake"
        where.write_text(body)
        where.chmod(where.stat().st_mode | stat.S_IXUSR)
        return where

    def test_a_driver_that_fails_is_reported_rather_than_read_as_agreement(self) -> None:
        case = differential.cases(seeds=1)[0]

        with self.assertRaises(differential.Usage):
            differential.ask(case, "/usr/bin/false")

    def test_a_driver_that_answers_differently_makes_the_run_fail(self) -> None:
        wrong = self.scripted("#!/bin/sh\ncat > /dev/null\necho 99\n")

        self.assertEqual(differential.run(["--seeds", "1", "--driver", str(wrong)]), 1)

    def test_a_run_of_many_wrong_answers_stops_reporting_after_a_handful(self) -> None:
        wrong = self.scripted("#!/bin/sh\ncat > /dev/null\necho 99\n")

        self.assertEqual(differential.run(["--seeds", "8", "--driver", str(wrong)]), 1)


@unittest.skipUnless(HAS_DRIVER, "the reference driver is not built")
class AgainstReferenceTest(unittest.TestCase):
    def test_the_model_agrees_with_the_reference_on_every_mode(self) -> None:
        for case in differential.cases(seeds=3):
            found = differential.disagreement(
                differential.ask(case, str(BUILT)), differential.replay(case)
            )

            self.assertIsNone(found, repr(case))

    def test_a_short_run_reports_clean(self) -> None:
        self.assertEqual(differential.run(["--seeds", "2"]), 0)


class EntryTest(unittest.TestCase):
    def test_a_run_with_no_driver_present_says_so_rather_than_passing(self) -> None:
        self.assertEqual(differential.main(["--driver", "/nowhere/at/all"]), 2)

    def test_an_option_it_does_not_know_is_reported(self) -> None:
        self.assertEqual(differential.main(["--nonsense"]), 2)


if __name__ == "__main__":
    unittest.main()
