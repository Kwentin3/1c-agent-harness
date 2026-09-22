from __future__ import annotations

import io
import json
import os
from pathlib import Path
import tempfile
import textwrap
import time
import unittest
from unittest import mock

from one_c_harness import eventlog_exporter


class EventLogExporterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.ib = self.root / "selected-ib"; self.ib.mkdir()
        self.epf = self.root / "eventlog.epf"; self.epf.write_bytes(b"epf")
        self.platform = self.root / "platform.py"
        self.xvfb = self.root / "xvfb-run"
        self.xvfb.write_text(textwrap.dedent("""\
            #!/bin/sh
            [ "$1" = "-a" ] && shift
            if [ "$1" = "-s" ]; then shift 2; fi
            exec "$@"
        """), encoding="utf-8")
        self.xvfb.chmod(0o755)
        self.libs = self.root / "libs"; self.libs.mkdir()
        self.fontconfig = self.root / "fonts.conf"; self.fontconfig.write_text("fonts")
        self.profile = self.root / "runtime.json"
        self.profile.write_text(json.dumps({
            "platform": str(self.platform), "xvfb": str(self.xvfb),
            "libs": str(self.libs), "fontconfig": str(self.fontconfig),
        }))
        self.work = self.root / "work"; self.work.mkdir()
        self.previous = {key: os.environ.get(key) for key in eventlog_exporter.ENVIRONMENT_KEYS}
        os.environ.update({
            "ONE_C_HARNESS_EVENTLOG_RUNTIME_PROFILE": str(self.profile),
            "ONE_C_HARNESS_EVENTLOG_INFOBASE": str(self.ib),
            "ONE_C_HARNESS_EVENTLOG_EPF": str(self.epf),
            "ONE_C_HARNESS_EVENTLOG_WORK_ROOT": str(self.work),
        })
        self.request = {
            "schemaVersion": 1, "operation": "unloadEventLog",
            "start": "2026-09-22T06:44:00", "end": "2026-09-22T06:45:00",
            "filters": {"event": "_$Session$_.Start", "level": "Information"},
            "columns": list(eventlog_exporter.COLUMNS), "maximumCount": 100, "maximumBytes": 1048576,
        }

    def tearDown(self) -> None:
        for key, value in self.previous.items():
            if value is None: os.environ.pop(key, None)
            else: os.environ[key] = value
        self.temporary.cleanup()

    def _platform(self, body: str) -> None:
        self.platform.write_text("#!/usr/bin/env python3\n" + textwrap.dedent(body), encoding="utf-8")
        self.platform.chmod(0o755)

    def test_fixed_selected_base_route_returns_fresh_xml_and_measures_cost(self) -> None:
        self._platform("""
            import pathlib, sys, time
            args=sys.argv[1:]; root=pathlib.Path(args[args.index('/C')+1])
            (root/'form-server-created').write_text('true')
            (root/'client-entered').write_text('true')
            (root/'server-entered').write_text('true')
            (root/'export-started').write_text('true'); time.sleep(.03)
            (root/'output.xml').write_text('<?xml version="1.0"?><v8e:EventLog xmlns:v8e="http://v8.1c.ru/eventLog"/>')
            (root/'export-returned').write_text('true')
            (root/'complete').write_text('true')
        """)
        xml, metrics = eventlog_exporter.run_once(self.request)

        self.assertIn(b"EventLog", xml)
        self.assertEqual(metrics["status"], "ok")
        self.assertEqual(metrics["selectedInfoBase"], "configured_file_infobase")
        self.assertGreaterEqual(metrics["lifecycleMilliseconds"], metrics["exportMilliseconds"])
        self.assertEqual(metrics["xmlBytes"], len(xml))
        self.assertEqual(metrics["exporterInvocations"], 1)
        self.assertNotIn(str(self.ib), json.dumps(metrics))
        self.assertNotIn(str(self.epf), json.dumps(metrics))

    def test_acquisition_byte_limit_stops_owned_process_before_completion(self) -> None:
        escaped = repr(str(self.root / "escaped"))
        self._platform(f"""
            import pathlib, sys, time
            args=sys.argv[1:]; root=pathlib.Path(args[args.index('/C')+1])
            (root/'client-entered').write_text('true'); (root/'server-entered').write_text('true'); (root/'export-started').write_text('true')
            with (root/'output.xml').open('wb') as stream:
                for _ in range(200): stream.write(b'x'*1024); stream.flush(); time.sleep(.01)
            pathlib.Path({escaped}).write_text('not killed')
        """)
        request = dict(self.request); request["maximumBytes"] = 4096
        with self.assertRaisesRegex(eventlog_exporter.ExportFailure, "byte_limit"):
            eventlog_exporter.run_once(request)
        time.sleep(.1)
        self.assertFalse((self.root / "escaped").exists())

    def test_invalid_request_and_untrusted_paths_fail_before_launch(self) -> None:
        marker = self.root / "launched"
        self._platform(f"import pathlib; pathlib.Path({str(marker)!r}).write_text('bad')\n")
        bad = dict(self.request); bad["path"] = "/tmp/injected"
        with self.assertRaisesRegex(eventlog_exporter.ExportFailure, "invalid_request"):
            eventlog_exporter.run_once(bad)
        self.assertFalse(marker.exists())

        self.epf.unlink(); self.epf.symlink_to(self.root / "missing")
        with self.assertRaisesRegex(eventlog_exporter.ExportFailure, "configuration_invalid"):
            eventlog_exporter.run_once(self.request)
        self.assertFalse(marker.exists())

    def test_failed_command_writes_safe_deployment_receipt(self) -> None:
        metrics = self.root / "failure.json"
        os.environ["ONE_C_HARNESS_EVENTLOG_METRICS"] = str(metrics)
        self._platform("""
            import pathlib, sys
            args=sys.argv[1:]; root=pathlib.Path(args[args.index('/C')+1])
            sys.stderr.write('wrapper failure at /private/runtime\\n')
            (root/'runtime.log').write_text('External data processor could not be opened')
            (root/'runtime.result').write_text('3')
            raise SystemExit(7)
        """)
        stdin = type("Input", (), {"buffer": io.BytesIO(json.dumps(self.request).encode())})()
        stdout = type("Output", (), {"buffer": io.BytesIO()})()
        standard_error = io.StringIO()
        with (
            mock.patch.object(eventlog_exporter.sys, "argv", ["one-c-eventlog-exporter"]),
            mock.patch.object(eventlog_exporter.sys, "stdin", stdin),
            mock.patch.object(eventlog_exporter.sys, "stdout", stdout),
            mock.patch.object(eventlog_exporter.sys, "stderr", standard_error),
        ):
            code = eventlog_exporter.main()
        self.assertEqual(code, 2)
        receipt = json.loads(metrics.read_text())
        self.assertEqual(receipt["status"], "failed")
        self.assertEqual(receipt["reasonCode"], "source_process_failed")
        diagnostic = receipt["diagnostic"]
        self.assertEqual(diagnostic["stage"], "enterprise_process")
        self.assertEqual(diagnostic["wrapperExitCode"], 7)
        self.assertEqual(diagnostic["receipts"], {
            "form-server-created": False, "client-entered": False, "server-entered": False, "export-started": False,
            "export-returned": False, "complete": False,
        })
        self.assertEqual(diagnostic["stderr"]["message"], "<path-redacted>")
        self.assertEqual(diagnostic["runtimeLog"]["message"], "External data processor could not be opened")
        self.assertEqual(diagnostic["dumpResult"]["message"], "3")
        self.assertNotIn(str(self.root), json.dumps(receipt))
        self.assertEqual(json.loads(standard_error.getvalue()), {
            "reasonCode": "source_process_failed", "stage": "enterprise_process",
            "message": "External data processor could not be opened",
        })

    def test_epf_source_has_default_managed_form_and_verified_entry_chain(self) -> None:
        source = Path(eventlog_exporter.__file__).with_name("eventlog_epf")
        root = (source / "Issue80EventLog.xml").read_text(encoding="utf-8-sig")
        form = (source / "Issue80EventLog/Forms/Main/Ext/Form.xml").read_text(encoding="utf-8-sig")
        module = (source / "Issue80EventLog/Forms/Main/Ext/Form/Module.bsl").read_text(encoding="utf-8-sig")
        self.assertIn("ExternalDataProcessor.Issue80EventLog.Form.Main", root)
        self.assertIn("<Form>Main</Form>", root)
        self.assertIn('<Event name="OnOpen">ПриОткрытии</Event>', form)
        self.assertIn('<Event name="OnCreateAtServer">ПриСозданииНаСервере</Event>', form)
        for required in ("&НаКлиенте", "Процедура ПриОткрытии(Отказ)", "Корень = ПараметрЗапуска", "ВыгрузитьНаСервере(Корень)", "&НаСервере", "Процедура ПриСозданииНаСервере(Отказ, СтандартнаяОбработка)", "ВыгрузитьЖурналРегистрации", "form-server-created", "client-entered", "server-entered", "export-started", "export-returned", "complete", "ПрекратитьРаботуСистемы"):
            self.assertIn(required, module)
        self.assertNotIn("Выполнить(", module)
        self.assertNotIn("Вычислить(", module)
        project = (Path(eventlog_exporter.__file__).parent.parent / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('one-c-eventlog-exporter = "one_c_harness.eventlog_exporter:main"', project)
        self.assertIn('"eventlog_epf/**/*.xml"', project)
        self.assertIn('"eventlog_epf/**/*.bsl"', project)


if __name__ == "__main__":
    unittest.main()
