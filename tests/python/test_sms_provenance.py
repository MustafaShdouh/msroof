"""Source/proxy/redaction safeguards; no model inference or private-data publishing."""
import copy
import json
import unittest

from training import audit_sms_provenance as audit


class SmsProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.policy = {"minimumSharedTokens": 8, "minimumTokenJaccard": .7, "minimumTokenSequenceRatio": .82}

    def test_wrapped_blocks_keep_routing_line_and_precise_offsets(self):
        text = "\r\nJO\r\nFirst wrapped\r\nmessage.\r\n \t\r\n\r\nSecond.\r\n"
        rows = audit.blocks(text)
        self.assertEqual(len(rows), 2)
        self.assertEqual((rows[0]["startLine"], rows[0]["endLine"]), (2, 4))
        for row in rows:
            self.assertEqual(text[row["startChar"]:row["endChar"]], row["text"])
            self.assertFalse(row["text"].endswith(("\r", "\n")))

    def test_attestation_cannot_cover_changed_sources_or_new_blocks(self):
        text = "one\n\ntwo"
        expected = audit.digest(text.encode())
        source = {"sha256": expected, "expectedBlocks": 2}
        self.assertEqual(len(audit.verified_blocks(source, text, expected, expected)), 2)
        for source_hash, copy_hash in (("changed", expected), (expected, "changed")):
            with self.subTest(source_hash=source_hash), self.assertRaises(ValueError):
                audit.verified_blocks(source, text, source_hash, copy_hash)
        with self.assertRaises(ValueError):
            audit.verified_blocks(source | {"expectedBlocks": 3}, text, expected, expected)

    def test_normalization_preserves_values_currency_and_status(self):
        self.assertEqual(audit.canonical("JO\r\nPaid ١٢٫٥٠ JOD"), audit.canonical("jo Paid 12.50 jod"))
        for text in ("JO Paid 13.50 JOD", "JO Paid 12.50 USD", "JO Declined 12.50 JOD"):
            self.assertNotEqual(audit.canonical("JO Paid 12.50 JOD"), audit.canonical(text))

    def test_text_and_numeric_matches_never_establish_parentage(self):
        seed = audit.indexed("JO\nPayment JOD 12.50 complete.")
        for text, method in (("JO\nPayment JOD 12.50 complete.", "exact_text"),
                             ("jo Payment JOD 12.50 complete.", "normalized_text"),
                             ("JO\nPayment JOD 99.50 complete.", "number_masked")):
            result = audit.overlap(seed, audit.indexed(text), self.policy)
            self.assertEqual(result["method"], method)
            self.assertIsNone(result["confirmedParentId"])
            if method == "number_masked":
                self.assertEqual(result["evidence"], "inferred_template_candidate")

    def test_lexical_similarity_is_only_a_candidate(self):
        left = "Payment completed from your account to recipient for a purchase today with balance available"
        right = "Payment completed from your account to recipient for a purchase yesterday with balance available"
        result = audit.overlap(audit.indexed(left), audit.indexed(right), self.policy)
        self.assertEqual(result["evidence"], "inferred_template_candidate")
        self.assertIsNone(result["confirmedParentId"])
        self.assertIsNone(audit.overlap(audit.indexed(left), audit.indexed("Call me tomorrow"), self.policy))

    def test_redaction_removes_seed_identifiers_preserving_financial_amounts(self):
        text = "JOD 12.500 debited from 1234*567 to AHMAD TEST as CliQ transfer on 21/02 at 10:30. Balance JOD 99.750. Ref # 12345678"
        draft, edits = audit.sanitize_draft(text)
        for secret in ("1234*567", "AHMAD TEST", "21/02", "10:30", "12345678"):
            self.assertNotIn(secret, draft)
        self.assertIn("12.500", draft)
        self.assertIn("99.750", draft)
        for edit in edits:
            self.assertEqual(draft[edit["sanitizedStart"]:edit["sanitizedEnd"]], edit["placeholder"])
        self.assertTrue(all(a["sourceEnd"] <= b["sourceStart"] for a, b in zip(edits, edits[1:])))

    def test_otp_and_tokens_are_not_confused_with_amounts(self):
        for text in ("975321 هو رمز المرور لمرة واحدة (OTP). المبلغ ٥ د.أ.",
                     "One Time Password: 975321. Purpose: purchase of amount 5 JOD."):
            draft, _ = audit.sanitize_draft(text)
            self.assertNotIn("975321", draft)
            self.assertTrue("٥" in draft or "5 JOD" in draft)
        draft, _ = audit.sanitize_draft("Voucher ABCDEFGH12\nqRsTUvWxYz")
        self.assertNotIn("ABCDEFGH12", draft)
        self.assertNotIn("qRsTUvWxYz", draft)

    def test_csv_view_allows_only_line_ending_normalization(self):
        record = {"text": "JO\nMessage", "label": "LABEL", "provider": "SOURCE", "type": None,
                  "expected_amount": None, "expected_merchant": None}
        csv_row = {k: "" if v is None else str(v) for k, v in record.items()}
        csv_row["text"] = "JO\r\nMessage"
        before = copy.deepcopy(csv_row)
        result = audit.compare_csv([csv_row], [record])
        self.assertFalse(result["exactFieldEquality"])
        self.assertTrue(result["equalAfterTextLineEndingNormalization"])
        self.assertEqual(result["textLineEndingDifferenceRows"], 1)
        self.assertEqual(csv_row, before)
        self.assertFalse(audit.compare_csv([csv_row | {"label": "OTHER"}], [record])["equalAfterTextLineEndingNormalization"])
        self.assertFalse(audit.compare_csv([], [record])["equalAfterTextLineEndingNormalization"])

    def test_cross_partition_proxy_is_reported_without_assigning_family_or_changing_rows(self):
        rows = [{"index": audit.indexed(text), "reference": {"currentPartition": fold}}
                for text, fold in (("Paid 12 JOD", "train"), ("Paid 99 JOD", "validation"))]
        before = copy.deepcopy(rows)
        result = audit.proxy_partition_overlap(rows)
        self.assertEqual(result["normalized"]["crossPartitionGroups"], 0)
        self.assertEqual(result["masked"]["crossPartitionGroups"], 1)
        self.assertEqual(result["masked"]["rowsInThoseGroups"], 2)
        self.assertEqual(rows, before)
        repeated = [{"index": audit.indexed("same notification"),
                     "reference": {"currentPartition": fold, "providerMetadata": provider, "existingLabel": "ANNOUNCEMENT"}}
                    for fold, provider in (("train", "source-a"), ("validation", "source-b"))]
        result = audit.proxy_partition_overlap(repeated)["normalized"]
        self.assertEqual(result["crossPartitionGroups"], 1)
        self.assertEqual(result["groupsAcrossProviderMetadata"], 1)
        self.assertEqual(result["groupsWithConflictingExistingLabels"], 0)

    @unittest.skipUnless((audit.ROOT / "DATA_YOU_WANT/ARAB_BANK.txt").exists() and
                         (audit.ROOT / "DATA_YOU_WANT/CAPITAL_BANK.txt").exists(), "Private seeds are local-only")
    def test_local_audit_preserves_inputs_and_keeps_records_private_and_unadmitted(self):
        before = audit.protected_hashes(audit.ROOT)
        private, public = audit.build_audit()
        self.assertEqual(audit.protected_hashes(audit.ROOT), before)
        self.assertEqual(len(private["records"]), sum(x["blocks"] for x in public["sourceFiles"]))
        for row in private["records"]:
            self.assertFalse(row["trainingEligible"])
            self.assertFalse(row["evaluationEligible"])
            self.assertIsNone(row["labels"])
            self.assertIsNone(row["sender"])
            self.assertIsNone(row["receivedAt"])
            self.assertIsNone(row["parentRecordIds"])
            self.assertTrue(all(x["confirmedParentId"] is None for x in row["exposureLinks"]))
        self.assertEqual(public["bioRowsVerifiedAsFixtureCopies"], public["bioRowsScanned"])
        rendered = json.dumps(public) + audit.readable(public)
        for key in ("sanitizedTextDraft", "textSha256", "sourceLocator", "exposureLinks"):
            self.assertNotIn(key, rendered)
        self.assertEqual(public["confirmedGeminiParentEdges"], 0)


if __name__ == "__main__":
    unittest.main()
