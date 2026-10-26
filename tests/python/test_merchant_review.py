"""Exercise saved-review integrity and independent bootstrap selection."""

from contextlib import redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("merchant_review", ROOT / "training/categories/review.py")
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


class MerchantReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.saved_paths = {key: getattr(review, key) for key in ("CANDIDATES", "REVIEWS", "BATCH_PATH", "HTML_PATH", "TAXONOMY", "EDGE_CASES", "BUSINESSES", "AMBIGUITIES")}
        review.EDGE_CASES = self.root / "edges.json"
        review.BUSINESSES = self.root / "businesses.jsonl"
        review.AMBIGUITIES = self.root / "ambiguities.json"
        for key, name in (("CANDIDATES", "candidates.jsonl"), ("REVIEWS", "reviews.jsonl"), ("BATCH_PATH", "batch.json"), ("HTML_PATH", "review.html"), ("TAXONOMY", "taxonomy.json")):
            setattr(review, key, self.root / name)
        review.TAXONOMY.write_text(json.dumps({"allowedCategories": ["Food", "Groceries"]}), encoding="utf-8")
        self.rows = [
            {"id": "one", "name": "Cafe", "brandGroup": "cafe", "cities": [], "proposedCategory": "Food", "origins": []},
            {"id": "two", "name": "Cafe Branch", "brandGroup": "cafe", "cities": [], "proposedCategory": "Food", "origins": []},
            {"id": "three", "name": "Grocery", "brandGroup": "grocery", "cities": [], "proposedCategory": "Groceries", "origins": []},
        ]
        review.CANDIDATES.write_text("".join(json.dumps(row) + "\n" for row in self.rows), encoding="utf-8")

    def tearDown(self):
        for key, value in self.saved_paths.items():
            setattr(review, key, value)
        self.temp.cleanup()

    def exported_decision(self, index=0, status="approved"):
        row = self.rows[index]
        return {"id": row["id"], "name": row["name"], "brandGroup": row["brandGroup"], "status": status, "category": row["proposedCategory"], "reviewer": "test reviewer", "notes": ""}

    def import_payload(self, rows):
        path = self.root / "export.json"
        path.write_text(json.dumps({"schemaVersion": "1.0.0", "reviews": rows}), encoding="utf-8")
        with redirect_stdout(io.StringIO()):
            return review.import_reviews(path)

    def test_invalid_batch_cannot_partially_change_saved_reviews(self):
        first = self.exported_decision()
        self.import_payload([first])
        before = review.REVIEWS.read_bytes()
        invalid = self.exported_decision(2)
        invalid["category"] = "Invented Category"
        with self.assertRaises(ValueError):
            self.import_payload([self.exported_decision(1), invalid])
        self.assertEqual(before, review.REVIEWS.read_bytes())

    def test_assistant_provenance_roundtrips_without_becoming_human(self):
        row = self.exported_decision()
        row.update(reviewer="Codex", reviewerType="assistant", notes="Sourced merchant default only.",
                   reviewEvidence=[{"url": "https://example.org/cafe", "summary": "Cafe listing."}])
        self.import_payload([row])
        saved = review.existing_reviews(review.indexed_candidates())[row["id"]]
        self.assertEqual(saved["reviewerType"], "assistant")
        self.assertEqual(saved["reviewEvidence"], row["reviewEvidence"])

    def test_assistant_requires_evidence_and_cannot_replace_human(self):
        human = self.exported_decision()
        self.import_payload([human])
        before = review.REVIEWS.read_bytes()
        assistant = {**human, "reviewer": "Codex", "reviewerType": "assistant"}
        with self.assertRaises(ValueError):
            self.import_payload([assistant])
        assistant.update(notes="Source checked.", reviewEvidence=[{"url": "https://example.org/", "summary": "Cafe."}])
        with self.assertRaisesRegex(ValueError, "cannot overwrite"):
            self.import_payload([assistant])
        self.assertEqual(review.REVIEWS.read_bytes(), before)

    def test_unknown_reviewer_type_rejected(self):
        with self.assertRaises(ValueError):
            self.import_payload([self.exported_decision() | {"reviewerType": "robot"}])

    def test_import_preserves_earlier_source_snapshot_when_candidates_change(self):
        self.import_payload([self.exported_decision()])
        first = review.read_lines(review.REVIEWS)[0]
        self.rows[0]["origins"] = [{"url": "https://example.org/new", "kind": "later_research"}]
        review.CANDIDATES.write_text("".join(json.dumps(row) + "\n" for row in self.rows), encoding="utf-8")
        self.import_payload([self.exported_decision(2)])
        stored = {row["id"]: row for row in review.read_lines(review.REVIEWS)}
        self.assertEqual(stored[first["id"]], first)
        self.assertEqual(review.existing_reviews(review.indexed_candidates())[first["id"]]["origins"], first["origins"])

    def test_reviews_survive_queue_regeneration(self):
        self.import_payload([self.exported_decision()])
        before = review.REVIEWS.read_bytes()
        with redirect_stdout(io.StringIO()):
            batch = review.create_batch(12)
        self.assertEqual(before, review.REVIEWS.read_bytes())
        self.assertNotIn("one", {row["id"] for row in batch["candidates"]})

    def test_batch_does_not_repeat_brand_groups(self):
        with redirect_stdout(io.StringIO()):
            batch = review.create_batch(12)
        self.assertEqual(len(batch["candidates"]), 2)

    def test_deferrals_are_not_training_labels(self):
        self.import_payload([self.exported_decision(status="needs_context")])
        saved = review.read_lines(review.REVIEWS)[0]
        self.assertIsNone(saved["category"])
        self.assertEqual(saved["labelScope"], "merchant_name")
        with redirect_stdout(io.StringIO()):
            batch = review.create_batch(12)
        self.assertNotIn("one", {row["id"] for row in batch["candidates"]})

    def test_approval_cannot_change_sourced_brand_or_unknown_id(self):
        row = self.exported_decision()
        row["brandGroup"] = "different-family"
        with self.assertRaises(ValueError):
            self.import_payload([row])
        row = self.exported_decision()
        row["id"] = "unknown"
        with self.assertRaises(ValueError):
            self.import_payload([row])

    def make_edge(self):
        case = {"id": "edge-one", "name": "Example grocery basket", "brandGroup": "grocery", "labelScope": "illustrative_transaction", "exampleText": "A grocery payment", "reviewQuestion": "Which category?", "possibleCategories": ["Groceries"], "sources": []}
        review.EDGE_CASES.write_text(json.dumps({"schemaVersion": "1.0.0", "cases": [case]}), encoding="utf-8")
        return case

    def test_scenario_review_preserves_text_and_scope(self):
        case = self.make_edge()
        row = {**case, "status": "approved", "category": "Groceries", "reviewer": "test reviewer"}
        self.import_payload([row])
        stored = review.read_lines(review.REVIEWS)[0]
        self.assertEqual(stored["exampleText"], case["exampleText"])
        self.assertEqual(stored["labelScope"], "illustrative_transaction")
        self.assertEqual(stored["dataKind"], "human_reviewed_illustrative_scenario")
        row["exampleText"] = "Changed after review"
        before = review.REVIEWS.read_bytes()
        with self.assertRaises(ValueError):
            self.import_payload([row])
        self.assertEqual(before, review.REVIEWS.read_bytes())

    def test_edge_batch_is_separate_from_merchant_batch(self):
        self.make_edge()
        with redirect_stdout(io.StringIO()):
            batch = review.create_edge_batch(12)
            regular = review.create_batch(12)
        self.assertEqual([row["id"] for row in batch["candidates"]], ["edge-one"])
        self.assertNotIn("edge-one", {row["id"] for row in regular["candidates"]})

    def test_business_mode_excludes_unverified_seed_names(self):
        business = {"businessId": "source-a", "name": "Public Grocer", "brandGroup": "public-grocer", "cities": ["Irbid"], "proposedCategories": ["Groceries"], "sources": [{"url": "https://example.test/grocer", "publisher": "Test directory"}]}
        review.BUSINESSES.write_text(json.dumps(business) + "\n", encoding="utf-8")
        with redirect_stdout(io.StringIO()):
            batch = review.create_batch(12, businesses_only=True)
        self.assertEqual([row["name"] for row in batch["candidates"]], ["Public Grocer"])

    def test_ambiguity_mode_is_sourced_and_preserves_earlier_reviews(self):
        business = {"businessId": "source-a", "name": "Public Grocer", "brandGroup": "public-grocer", "cities": ["Irbid"], "proposedCategories": ["Groceries"], "sources": [{"url": "https://example.test/grocer", "publisher": "Test directory"}]}
        review.BUSINESSES.write_text(json.dumps(business) + "\n", encoding="utf-8")
        review.AMBIGUITIES.write_text(json.dumps({"businesses": [{"name": "Public Grocer", "question": "Which default?", "categories": ["Food", "Groceries"]}]}), encoding="utf-8")
        self.import_payload([self.exported_decision()])
        before = review.REVIEWS.read_bytes()
        with redirect_stdout(io.StringIO()):
            batch = review.create_ambiguous_batch(12)
        self.assertEqual([row["name"] for row in batch["candidates"]], ["Public Grocer"])
        self.assertEqual(batch["candidates"][0]["reviewMode"], "ambiguity")
        self.assertEqual(before, review.REVIEWS.read_bytes())


if __name__ == "__main__":
    unittest.main()
