"""Check business identity deduplication, provenance and honest ranking fields."""

import importlib.util
import copy
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("build_business_shortlist", ROOT / "training/categories/shortlist.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class BusinessShortlistTests(unittest.TestCase):
    def test_assistant_labels_never_count_as_human_and_human_wins(self):
        row = {}
        assistant = {"id": "ai", "category": "Food", "reviewerType": "assistant"}
        builder.apply_category_reviews(row, [assistant])
        self.assertIsNone(row["humanConfirmedCategory"])
        self.assertEqual(row["assistantReviewedCategory"], "Food")
        self.assertEqual(row["labelStatus"], "assistant_reviewed_merchant_default")
        builder.apply_category_reviews(row, [assistant, {"id": "human", "category": "Groceries"}])
        self.assertEqual(row["humanConfirmedCategory"], "Groceries")
        self.assertEqual(row["labelStatus"], "human_reviewed_merchant_default")

    @classmethod
    def setUpClass(cls):
        cls.pool, cls.extracts = builder.build_pool()
        cls.saved = [json.loads(line) for line in builder.OUTPUT.read_text(encoding="utf-8").splitlines()]
        cls.rows = builder.preserve_selection(cls.pool, cls.saved)

    def test_enrichment_preserves_identity_and_reviewed_labels(self):
        rebuilt = builder.preserve_selection(list(reversed(self.pool)), self.saved)
        fields = ("businessId", "brandGroup", "name", "cities", "humanConfirmedCategory", "labelStatus")
        self.assertEqual([[row[field] for field in fields] for row in rebuilt],
                         [[row[field] for field in fields] for row in self.saved])
        with self.assertRaises(ValueError):
            builder.preserve_selection(self.pool[:-1], self.pool)

    def test_arabic_alias_provenance(self):
        evidence = json.loads(builder.ARABIC_ALIASES.read_text(encoding="utf-8"))["aliases"]
        rows = {row["name"]: row for row in self.rows}
        for item in evidence:
            row = rows[item["businessName"]]
            self.assertIn(item["alias"], row["aliases"])
            self.assertTrue(any(source["listedName"] == item["alias"] and source["url"] == item["url"]
                                and source.get("identityEvidence") for source in row["sources"]))

    def test_alias_collision_and_unknown_business_rejected_atomically(self):
        rows = [{"name": "First", "businessId": "one", "aliases": set(), "sources": []},
                {"name": "Second", "businessId": "two", "aliases": set(), "sources": []}]
        item = {"businessName": "First", "alias": "متجر", "url": "https://example.org/",
                "publisher": "Test", "accessedOn": "2026-10-24", "type": "official_arabic_name",
                "identityEvidence": "Test only"}
        before = copy.deepcopy(rows)
        for invalid in (item | {"businessName": "Unknown"}, item | {"businessName": "Second"},
                        item | {"url": ""}):
            with self.assertRaises(ValueError):
                builder.enrich_aliases(rows, [item, invalid])
            self.assertEqual(rows, before)

    def test_exactly_200_businesses_without_alias_rows(self):
        self.assertEqual(len(self.rows), 200)
        seen = set()
        for row in self.rows:
            keys = {builder.normalize(name) for name in [row["name"]] + row["aliases"]}
            self.assertFalse(keys & seen)
            seen.update(keys)

    def test_each_city_has_explicit_source_evidence(self):
        for row in self.rows:
            sourced_cities = {city for source in row["sources"] for city in source["cities"]}
            self.assertEqual(set(row["cities"]), sourced_cities)
            self.assertTrue(row["sources"])
            self.assertTrue(all(source["url"].startswith("https://") for source in row["sources"]))

    def test_no_fabricated_popularity_or_certainty(self):
        self.assertTrue(all(row["popularityRank"] is None and row["estimatedCorrectnessPct"] is None for row in self.rows))
        for row in self.rows:
            for evidence in row["popularityEvidence"]:
                self.assertGreaterEqual(evidence["reportedReviewCount"], 0)
                self.assertIn(evidence["sourceUrl"], {source["url"] for source in row["sources"]})

    def test_both_cities_and_coverage_anchors_represented(self):
        self.assertGreaterEqual(sum("Irbid" in row["cities"] for row in self.rows), 60)
        names = {builder.normalize(row["name"]) for row in self.rows}
        self.assertTrue({builder.normalize(name) for name in self.extracts["coverageAnchors"]}.issubset(names))


if __name__ == "__main__":
    unittest.main()
