"""Tests for the Sovereign Harness.

Standard library only, so the runtime's own tests carry no dependency either.
Run with: python3 -m unittest discover -s tests   (or pytest)
"""
import datetime as dt
import importlib.util
import tempfile
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("harness", BASE / "harness.py")
harness = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(harness)


class YamlSubset(unittest.TestCase):
    def test_scalars_and_nesting(self):
        got = harness.yaml_load(
            "a: 1\n"
            "b: two\n"
            "c:\n"
            "  d: true\n"
            "  e: null\n"
            "f: 'quoted: colon'\n"
        )
        self.assertEqual(
            got, {"a": 1, "b": "two", "c": {"d": True, "e": None}, "f": "quoted: colon"})

    def test_sequences_of_scalars_and_maps(self):
        got = harness.yaml_load(
            "roster:\n"
            "  - id: one\n"
            "    type: body\n"
            "  - id: two\n"
            "    type: person\n"
            "tiers:\n"
            "  - T1\n"
            "  - T2\n"
        )
        self.assertEqual(got["roster"],
                         [{"id": "one", "type": "body"}, {"id": "two", "type": "person"}])
        self.assertEqual(got["tiers"], ["T1", "T2"])

    def test_sequence_at_the_key_indent(self):
        got = harness.yaml_load("items:\n- a\n- b\nafter: x\n")
        self.assertEqual(got, {"items": ["a", "b"], "after": "x"})

    def test_folded_and_literal_blocks(self):
        got = harness.yaml_load(
            "folded: >-\n"
            "  one line\n"
            "  joined\n"
            "literal: |-\n"
            "  kept\n"
            "  apart\n"
            "next: done\n"
        )
        self.assertEqual(got["folded"], "one line joined")
        self.assertEqual(got["literal"], "kept\napart")
        self.assertEqual(got["next"], "done")

    def test_comments_are_stripped_but_not_inside_quotes(self):
        got = harness.yaml_load("# leading\na: b  # trailing\nc: 'x # y'\n")
        self.assertEqual(got, {"a": "b", "c": "x # y"})

    def test_round_trip_through_the_emitter(self):
        value = {"verdict": "HOLD", "gaps": [{"principal": "Ukraine", "gap": "no file"}],
                 "count": 3, "flag": False, "note": "a: colon"}
        self.assertEqual(harness.yaml_load(harness.yaml_dump(value)), value)

    def test_the_estate_s_own_records_parse(self):
        for path in [BASE / "standards/assembly-spec.yaml",
                     BASE.parent / "Horus/boards/ukraine.yaml",
                     BASE.parent / "Talleyrand/manifest.yaml",
                     BASE.parent / "Talleyrand/deeds/index.yaml",
                     BASE.parent / "config.yaml"]:
            with self.subTest(path=path.name):
                got = harness.yaml_load(path.read_text(encoding="utf-8"))
                self.assertIsInstance(got, dict)
                self.assertTrue(got)

    def test_deed_index_order_is_recoverable(self):
        index = harness.yaml_load(
            (BASE.parent / "Talleyrand/deeds/index.yaml").read_text(encoding="utf-8"))
        self.assertEqual(len(index["deeds"]), 19)
        self.assertEqual(index["deeds"][0]["id"], "0")
        ratified = [d for d in index["deeds"] if d["ratification"] == "OWNER_RATIFIED"]
        self.assertEqual([d["id"] for d in ratified], ["C1"])


class PrincipalFile(unittest.TestCase):
    def test_header_is_read_and_tier_bodies_are_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "p.md"
            path.write_text(
                "# Principal File\n\n"
                "- Principal name: Test Body\n"
                "- Type: body\n"
                "- Completeness: PENDING_PROBE\n"
                "- T1 last refresh: 2026-07-26\n"
                "- T1 status: FILLED\n"
                "- T3 status: THIN\n"
                "\n## T1 OWN WORDS\n\n- T4 status: NOT A HEADER LINE\n",
                encoding="utf-8")
            header = harness.read_principal_file(path)
        self.assertEqual(header["principal_name"], "Test Body")
        self.assertEqual(header["tiers"]["T1"], {"refreshed": "2026-07-26", "status": "FILLED"})
        self.assertEqual(header["tiers"]["T3"]["status"], "THIN")
        self.assertNotIn("T4", header["tiers"])


class ParityGate(unittest.TestCase):
    def _estate(self, tmp, files):
        horus = Path(tmp) / "Horus" / "files"
        horus.mkdir(parents=True)
        for name, body in files.items():
            (horus / name).write_text(body, encoding="utf-8")
        return Path(tmp)

    def _file(self, refresh="2026-08-04", statuses=("FILLED",) * 5,
              language="Russian", language_state="ORIGINAL"):
        lines = ["# Principal File", "", "- Principal name: X", "- Type: body",
                 "- Assembly date: 2026-08-04", "- Completeness: PENDING_PROBE"]
        for tier, status in zip(harness.TIERS, statuses):
            lines += ["- %s last refresh: %s" % (tier, refresh),
                      "- %s status: %s" % (tier, status)]
            if tier == "T1":
                lines += ["- T1 language: %s" % language,
                          "- T1 language state: %s" % language_state]
        return "\n".join(lines) + "\n## T1 OWN WORDS\n"

    def _board(self, roster):
        return {"board": "test", "board_type": "war", "roster": roster,
                "decay_tolerance_days": {"T1": 90, "T2": 30, "T3": 60, "T4": 7, "T5": 30},
                "gate_rule": "test"}

    def test_pass_when_every_gate_tier_is_filled_and_fresh(self):
        with tempfile.TemporaryDirectory() as tmp:
            estate = self._estate(tmp, {"a.md": self._file(), "b.md": self._file()})
            board = self._board([
                {"id": "a", "name": "A", "type": "body", "file": "files/a.md"},
                {"id": "b", "name": "B", "type": "person", "file": "files/b.md"}])
            got = harness.parity(estate, board, dt.date(2026, 8, 5))
        self.assertEqual(got["verdict"], "PASS")
        self.assertEqual(got["gaps"], [])

    def test_hold_when_a_principal_has_no_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            estate = self._estate(tmp, {"a.md": self._file()})
            board = self._board([
                {"id": "a", "name": "A", "type": "body", "file": "files/a.md"},
                {"id": "b", "name": "B", "type": "body", "file": "files/b.md"}])
            got = harness.parity(estate, board, dt.date(2026, 8, 5))
        self.assertEqual(got["verdict"], "HOLD")
        self.assertEqual(got["gap_count"], 1)
        self.assertIn("not been gathered", got["gaps"][0]["gap"])
        absent = [p for p in got["principals"] if p["id"] == "b"][0]
        self.assertEqual(absent["file_state"], "ABSENT")
        self.assertEqual(absent["tiers"]["T1"]["status"], "NOT_GATHERED")

    def test_hold_when_a_gate_tier_is_thin(self):
        with tempfile.TemporaryDirectory() as tmp:
            estate = self._estate(
                tmp, {"a.md": self._file(statuses=("FILLED", "THIN", "FILLED",
                                                   "FILLED", "FILLED"))})
            board = self._board([{"id": "a", "name": "A", "type": "body",
                                  "file": "files/a.md"}])
            got = harness.parity(estate, board, dt.date(2026, 8, 5))
        self.assertEqual(got["verdict"], "HOLD")
        self.assertIn("T2 is THIN", got["gaps"][0]["gap"])

    def test_hold_when_the_field_tier_is_stale_on_a_war_board(self):
        with tempfile.TemporaryDirectory() as tmp:
            estate = self._estate(tmp, {"a.md": self._file(refresh="2026-07-20")})
            board = self._board([{"id": "a", "name": "A", "type": "body",
                                  "file": "files/a.md"}])
            got = harness.parity(estate, board, dt.date(2026, 8, 5))
        self.assertEqual(got["verdict"], "HOLD")
        self.assertTrue(any("T4 is STALE" in g["gap"] for g in got["gaps"]))
        self.assertTrue(all("T1" not in g["gap"] for g in got["gaps"]))

    def test_a_non_gate_tier_never_holds_the_board(self):
        with tempfile.TemporaryDirectory() as tmp:
            estate = self._estate(
                tmp, {"a.md": self._file(statuses=("FILLED", "FILLED", "EMPTY",
                                                   "FILLED", "EMPTY"))})
            board = self._board([{"id": "a", "name": "A", "type": "body",
                                  "file": "files/a.md"}])
            got = harness.parity(estate, board, dt.date(2026, 8, 5))
        self.assertEqual(got["verdict"], "PASS")
        self.assertEqual(got["principals"][0]["tiers"]["T3"]["status"], "EMPTY")

    def test_a_filled_t1_on_translation_alone_is_a_gap(self):
        with tempfile.TemporaryDirectory() as tmp:
            estate = self._estate(tmp, {"a.md": self._file(
                language="English (translation of Russian originals)",
                language_state="TRANSLATION_ONLY")})
            board = self._board([{"id": "a", "name": "A", "type": "body",
                                  "file": "files/a.md"}])
            got = harness.parity(estate, board, dt.date(2026, 8, 5))
        self.assertEqual(got["verdict"], "HOLD")
        self.assertTrue(any("language state is TRANSLATION_ONLY" in g["gap"]
                            for g in got["gaps"]))
        self.assertEqual(got["language_mark"]["not_heard_in_own_words"], ["A"])
        self.assertTrue(got["language_mark"]["carries_mark"])

    def test_original_language_t1_is_heard_in_own_words(self):
        with tempfile.TemporaryDirectory() as tmp:
            estate = self._estate(tmp, {"a.md": self._file()})
            board = self._board([{"id": "a", "name": "A", "type": "body",
                                  "file": "files/a.md"}])
            got = harness.parity(estate, board, dt.date(2026, 8, 5))
        self.assertEqual(got["verdict"], "PASS")
        self.assertEqual(got["language_mark"]["heard_in_own_words"], ["A"])
        self.assertFalse(got["language_mark"]["carries_mark"])
        self.assertEqual(got["principals"][0]["tiers"]["T1"]["language"], "Russian")

    def test_an_ungathered_principal_is_not_heard_in_own_words(self):
        with tempfile.TemporaryDirectory() as tmp:
            estate = self._estate(tmp, {})
            board = self._board([{"id": "a", "name": "A", "type": "body",
                                  "file": "files/a.md"}])
            got = harness.parity(estate, board, dt.date(2026, 8, 5))
        self.assertEqual(got["language_mark"]["not_heard_in_own_words"], ["A"])

    def test_the_live_ukraine_board_holds(self):
        estate = BASE.parent
        board = harness.yaml_load(
            (estate / "Horus/boards/ukraine.yaml").read_text(encoding="utf-8"))
        got = harness.parity(estate, board, dt.date(2026, 8, 5))
        self.assertEqual(got["verdict"], "HOLD")
        gathered = [p["id"] for p in got["principals"] if p["file_state"] == "PRESENT"]
        self.assertEqual(sorted(gathered),
                         ["russian-federation", "russian-federation--putin"])


if __name__ == "__main__":
    unittest.main()
