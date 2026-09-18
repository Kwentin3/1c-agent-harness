from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest

from one_c_harness import techlog_observation


class TechLogObservationTests(unittest.TestCase):
    def test_observe_then_expand_uses_a_stable_safe_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            source = Path(temporary) / "techlog"
            log = source / "1cv8t_1" / "26091812.log"
            log.parent.mkdir(parents=True)
            log.write_text(
                "12:00.000001-0,EXCP,1,process=123,Descr='first private detail'\n"
                "detail line one\n"
                "12:00.000002-0,EXCP,1,process=124,Descr='second private detail'\n"
                "detail line two\n"
                "12:00.000003-0,SESN,1,Usr=roman\n",
                encoding="utf-8",
            )
            project.mkdir()
            previous = os.environ.get("ONE_C_HARNESS_TECHLOG_ROOT")
            os.environ["ONE_C_HARNESS_TECHLOG_ROOT"] = str(source)
            try:
                observed = techlog_observation.observe(project, "260918", "12:00.000000", "12:00.000999", ["EXCP"], 10)
                log.write_text(log.read_text(encoding="utf-8") + "12:00.000004-0,EXCP,1,Descr='later'\n", encoding="utf-8")
                page_one = techlog_observation.expand(project, observed["groups"][0]["ref"], 0, 1)
                page_two = techlog_observation.expand(project, observed["groups"][0]["ref"], 1, 1)
            finally:
                if previous is None:
                    os.environ.pop("ONE_C_HARNESS_TECHLOG_ROOT", None)
                else:
                    os.environ["ONE_C_HARNESS_TECHLOG_ROOT"] = previous

        self.assertEqual(observed["status"], "ok")
        self.assertEqual(observed["summary"], {"recordCount": 2, "source": "1c_techlog", "window": {"date": "260918", "start": "12:00.000000", "end": "12:00.000999"}})
        self.assertEqual(observed["groups"][0]["event"], "EXCP")
        self.assertEqual(observed["groups"][0]["count"], 2)
        self.assertTrue(observed["snapshot"]["stable"])
        self.assertEqual(page_one["records"][0]["sourceTimeToken"], "12:00.000001")
        self.assertEqual(page_two["records"][0]["sourceTimeToken"], "12:00.000002")
        self.assertTrue(page_one["truncated"])
        rendered = json.dumps([page_one, page_two])
        self.assertNotIn("private detail", rendered)
        self.assertNotIn("process=", rendered)
        self.assertNotIn("later", rendered)
        self.assertNotIn(str(source), rendered)

    def test_unavailable_source_is_distinct_from_empty_window(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            previous = os.environ.pop("ONE_C_HARNESS_TECHLOG_ROOT", None)
            try:
                unavailable = techlog_observation.observe(project, "260918", "12:00.000000", "12:00.000999", ["EXCP"], 10)
            finally:
                if previous is not None:
                    os.environ["ONE_C_HARNESS_TECHLOG_ROOT"] = previous
        self.assertEqual(unavailable["status"], "unavailable")
        self.assertEqual(unavailable["reasonCode"], "source_unavailable")


if __name__ == "__main__":
    unittest.main()
