"""Hold this decompressor's constants to hardware.json, and to their standing.

No manufacturer document names the SPC7110 and no recording of one is on this
machine, so both upper rungs of the ladder are empty. Every constant here says
so. The point of the file is that a reader cannot mistake agreement with a
reference implementation for a measurement of hardware, and that a constant
cannot quietly acquire a citation it does not have.
"""

import json
import sys
import unittest
from pathlib import Path
from typing import Any, override

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from spc7110 import decompressor

HERE = Path(__file__).resolve().parent


def declared(name: str) -> dict[str, Any]:
    held = json.loads((HERE / name).read_text())
    assert isinstance(held, dict), f"{name} does not hold an object"
    return held


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
        modes = self.facts["modes"]["value"]

        self.assertEqual(tuple(modes), decompressor.MODES)

    def test_the_coder_keeps_the_declared_number_of_contexts(self) -> None:
        contexts = self.facts["contexts"]["value"]

        self.assertEqual(contexts, decompressor.CONTEXTS)

    def test_the_buffer_is_the_declared_size(self) -> None:
        buffered = self.facts["bufferBytes"]["value"]

        self.assertEqual(buffered, decompressor.BUFFER_BYTES)

    def test_and_the_record_says_that_size_is_not_a_character_size(self) -> None:
        note = self.facts["bufferBytes"]["note"]

        self.assertIn("coincidence rather than a derivation", note)

    def test_the_interval_starts_at_the_declared_width(self) -> None:
        span = self.facts["spanFull"]["value"]

        self.assertEqual(span, decompressor.SPAN_FULL)

    def test_and_renormalises_below_the_declared_threshold(self) -> None:
        threshold = self.facts["renormaliseBelow"]["value"]

        self.assertEqual(threshold, decompressor.RENORMALISE_BELOW)

    def test_the_threshold_is_half_the_interval(self) -> None:
        self.assertEqual(decompressor.RENORMALISE_BELOW, decompressor.SPAN_FULL >> 1)


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
