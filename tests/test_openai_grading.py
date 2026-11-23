"""Exercise the actual reservation and parsing paths without a credential or network."""
import base64
import calendar
import io
import json
import sys
import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
import buyer_queue
import grade_expertise
import openai_grading as grading
import tag_capabilities


class Grading(unittest.TestCase):
    def test_calendar_ceiling(self):
        for month in range(1, 13):
            for year in (2024, 2026):
                n = calendar.monthrange(year, month)[1]
                self.assertLessEqual(n * 2 * grading.allowance(date(year, month, 1)), 10 * grading.NANOS)

    def test_concurrent_runs_and_retries(self):
        saved = {}

        def ledger(args, payload=None):
            if not payload:
                if not saved:
                    return SimpleNamespace(returncode=1, stderr="HTTP 404")
                return SimpleNamespace(returncode=0, stdout=json.dumps(saved))
            self.assertEqual(payload.get("sha"), saved.get("sha"))
            saved.update(content=payload["content"], sha=payload["content"])
            return SimpleNamespace(returncode=0, stdout=json.dumps({"content": saved}))

        response = {"usage": {"prompt_tokens": 40, "completion_tokens": 10,
                              "prompt_tokens_details": {"cached_tokens": 20}},
                    "choices": [{"finish_reason": "stop", "message": {"content": "{}"}}]}
        with patch.object(grading, "gh", ledger), patch.dict("os.environ", OPENAI_API_KEY="test"):
            s = grading.Session("tasks")
            with self.assertRaises(grading.StopGrading):
                grading.Session("tasks")
            with patch("urllib.request.urlopen", return_value=io.BytesIO(json.dumps(response).encode())):
                self.assertEqual(s.grade("rubric", "doc", 50), "{}")
            metered = grading.token_cost(40, 10, 20)
            error = HTTPError("", 429, "quota", {}, io.BytesIO(b'{"error":{"code":"credit_balance_exhausted"}}'))
            with patch("urllib.request.urlopen", side_effect=error), self.assertRaises(grading.StopGrading):
                s.grade("rubric", "doc", 50)
            self.assertEqual(s.record["nanos"], metered)
            with patch("urllib.request.urlopen", side_effect=TimeoutError), self.assertRaises(grading.StopGrading):
                s.grade("rubric", "doc", 50)
            self.assertGreater(s.record["nanos"], metered)
            s.close()
            recorded = json.loads(base64.b64decode(saved["content"]))
            self.assertEqual(recorded["calls"], 1)
            resumed = grading.Session("tasks")
            self.assertEqual(resumed.remaining, grading.allowance(s.day) - recorded["nanos"])
            with patch("urllib.request.urlopen") as post, self.assertRaises(grading.StopGrading):
                resumed.grade("x", "y", 200000)
            post.assert_not_called()

    def test_grades_need_source_evidence(self):
        grade = {"verdict": "solid", "expertise": 71, "note": "Includes a worked SQL query.",
                 "evidence": "select id from users"}
        self.assertEqual(grade_expertise.parse_grade(json.dumps(grade), grade["evidence"]), grade)
        for doc, score in [("unrelated text", 71), (grade["evidence"], 92)]:
            with self.assertRaises(ValueError):
                grade_expertise.parse_grade(json.dumps(dict(grade, expertise=score)), doc)
        self.assertIsNone(grade_expertise.parse_grade('{"verdict":null}', "text"))
        tag = {"tag": "sql", "evidence": "query tables", "confidence": 0.9}
        parse = lambda values: tag_capabilities.parse_tags(json.dumps({"tags": values}), {"sql"}, "query tables")
        self.assertEqual(parse([]), [])
        self.assertEqual(parse([tag]), [("sql", 0.9, "query tables")])
        for values in ([tag, tag], [dict(tag, confidence=0.3)], [dict(tag, evidence="Capability name")]):
            with self.assertRaises(ValueError):
                parse(values)

    def test_buyer_work_and_discovery_both_advance(self):
        rows = [(x,) for x in "abcdefghi"]
        with patch.object(buyer_queue, "priority", return_value=dict(zip("ihgfed", range(6)))):
            self.assertEqual(buyer_queue.select(rows, "tasks", 7), [(x,) for x in "ihgfaed"])


if __name__ == "__main__":
    unittest.main()
