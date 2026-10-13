"""Controlled Week 6 checks using explicit fixtures; no AirSim or Roboflow.

Run from the project root:
    python -m scripts.test_mission_outcome

Fixture images and traces are temporary and clearly marked as synthetic.
These checks establish policy/execution behavior, not smoke-model accuracy.
"""

import asyncio
import base64
from contextlib import redirect_stdout
from dataclasses import dataclass
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

from scripts.test_active_inspection import run_mission
from src.inspection.inspection_result import InspectionResult
from src.mission.decision_policy import evaluate_inspection
from src.mission.mission_outcome import MissionOutcome


@dataclass
class DispatchFixture:
    """Synthetic arrival payload, without importing the simulator adapter."""

    target: dict
    actual_north: float = 5.0
    actual_east: float = 10.0
    actual_down: float = -5.0
    arrived: bool = True


class AdapterFixture:
    """Record cleanup calls and optionally fail one or more operations."""

    def __init__(self, failures=()):
        self.calls = []
        self.failures = set(failures)

    def call(self, name):
        self.calls.append(name)
        if name in self.failures:
            raise RuntimeError(f"Synthetic {name} failure")

    def connect(self):
        self.call("connect")

    def prepare_drone(self):
        self.call("prepare")

    def start_rgb_camera(self):
        self.call("camera")

    async def takeoff(self):
        self.call("takeoff")

    async def return_home(self):
        self.call("return_home")

    async def land(self):
        self.call("land")

    def shutdown_drone(self):
        self.call("shutdown")

    def disconnect(self):
        self.call("disconnect")


class MissionOutcomeChecks(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output_dir = Path(self.temp.name)
        self.inspection_id = "inspection_controlled"
        self.evidence = self.output_dir / "synthetic_fixture.png"
        # A tiny synthetic PNG; never passed to a real detector.
        self.evidence.write_bytes(base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aL1sAAAAASUVORK5CYII="
        ))

    def result(self, case):
        common = {"inspection_id": self.inspection_id}
        if case == "positive":
            return InspectionResult(
                **common, completed=True, detected=True, confidence=0.70,
                evidence_path=str(self.evidence),
            )
        if case == "negative":
            return InspectionResult(
                **common, completed=True, detected=False,
                evidence_path=str(self.evidence),
            )
        return InspectionResult(
            **common, completed=False,
            evidence_path=str(self.evidence) if case == "perception_failure" else None,
            error="Synthetic perception failure" if case == "perception_failure"
            else "Synthetic RGB capture timeout",
        )

    def run_flow(self, result, failures=(), *, dispatch_error=False):
        adapter = AdapterFixture(failures)
        request = SimpleNamespace(
            inspection_id=self.inspection_id,
            to_dict=lambda: {
                "inspection_id": self.inspection_id,
                "source_event": {"camera_id": "camera_controlled", "synthetic": True},
                "reason": "suspected_smoke",
                "search_region_id": "sector_test",
            },
        )

        async def dispatch(*args, **kwargs):
            if dispatch_error:
                raise RuntimeError("Synthetic dispatch failure")
            return DispatchFixture({"north": 5.0, "east": 10.0, "down": -5.0})

        async def inspect(*args, **kwargs):
            return result

        output = io.StringIO()
        error = None
        with redirect_stdout(output):
            try:
                asyncio.run(run_mission(
                    request, adapter,
                    SimpleNamespace(dispatch=dispatch),
                    SimpleNamespace(inspect=inspect),
                    self.output_dir,
                    evidence_source="SYNTHETIC controlled fixture; no live camera",
                ))
            except Exception as exc:
                error = exc
        trace = json.loads(
            (self.output_dir / f"{self.inspection_id}_trace.json").read_text(encoding="utf-8")
        )
        return adapter, trace, output.getvalue(), error

    def test_four_policy_cases_serialize_and_preserve_identifier(self):
        cases = {
            "positive": ("request_human_review", "smoke_observed"),
            "negative": ("terminate", "no_smoke_observed"),
            "capture_failure": ("request_human_review", "inspection_failed"),
            "perception_failure": ("request_human_review", "inspection_failed"),
        }
        for case, (decision, reason) in cases.items():
            with self.subTest(case=case):
                result = self.result(case)
                outcome = evaluate_inspection(result)
                self.assertEqual(outcome, evaluate_inspection(result))
                self.assertEqual(json.loads(json.dumps(outcome.to_dict())), {
                    "inspection_id": self.inspection_id, "decision": decision, "reason": reason,
                })

    def test_outcome_rejects_empty_or_nonstring_identifiers(self):
        for inspection_id in ("", " ", None, 123):
            with self.subTest(inspection_id=inspection_id), self.assertRaises(ValueError):
                MissionOutcome(inspection_id, "terminate", "no_smoke_observed")

    def test_outcome_rejects_unsupported_values_and_combinations(self):
        for decision, reason in (
            ("terminate", "smoke_observed"),
            ("terminate", "inspection_failed"),
            ("request_human_review", "no_smoke_observed"),
            ("email_sent", "smoke_observed"),
            ("request_human_review", "dangerous_fire"),
        ):
            with self.subTest(decision=decision, reason=reason), self.assertRaises(ValueError):
                MissionOutcome(self.inspection_id, decision, reason)

    def test_policy_rejects_nonresult_inputs(self):
        for value in (None, {}, self.result("negative").to_dict()):
            with self.subTest(value=value), self.assertRaises(TypeError):
                evaluate_inspection(value)

    def test_policy_rejects_nonboolean_completion(self):
        for completed in (1, 0, "true"):
            result = InspectionResult(
                self.inspection_id, completed,
                detected=False if completed else None,
                evidence_path=str(self.evidence) if completed else None,
                error=None if completed else "Synthetic failure",
            )
            with self.subTest(completed=completed), self.assertRaises(ValueError):
                evaluate_inspection(result)

    def test_policy_revalidates_malformed_result(self):
        result = self.result("negative")
        object.__setattr__(result, "detected", None)
        with self.assertRaises(ValueError):
            evaluate_inspection(result)

    def test_policy_has_no_second_confidence_threshold(self):
        for confidence in (0.0, 0.50, 0.99, 1.0):
            result = InspectionResult(
                self.inspection_id, True, True, confidence, str(self.evidence),
            )
            with self.subTest(confidence=confidence):
                self.assertEqual(evaluate_inspection(result).reason, "smoke_observed")

    def test_completed_flows_preserve_source_result_and_cleanup(self):
        for case in ("positive", "negative"):
            with self.subTest(case=case):
                result = self.result(case)
                adapter, trace, output, error = self.run_flow(result)
                self.assertIsNone(error)
                self.assertEqual(trace["inspection"], result.to_dict())
                self.assertEqual(trace["outcome"], evaluate_inspection(result).to_dict())
                self.assertEqual(trace["request"]["inspection_id"], result.inspection_id)
                self.assertTrue(trace["synthetic_monitoring_trigger"])
                self.assertIn("SYNTHETIC", trace["inspection_evidence_source"])
                self.assertIsNotNone(trace["dispatch"])
                self.assertEqual(trace["cleanup"], {"completed": True, "errors": []})
                self.assertIsNone(trace["execution_error"])
                self.assertEqual(adapter.calls[-4:], ["return_home", "land", "shutdown", "disconnect"])
                self.assertIn("[PASS]", output)
                self.assertEqual("[REVIEW REQUEST]" in output, case == "positive")

    def test_inspection_failure_records_review_then_raises_and_cleans_up(self):
        for case in ("capture_failure", "perception_failure"):
            with self.subTest(case=case):
                result = self.result(case)
                adapter, trace, output, error = self.run_flow(result)
                self.assertIsInstance(error, RuntimeError)
                self.assertIn(result.error, str(error))
                self.assertEqual(trace["inspection"], result.to_dict())
                self.assertEqual(trace["outcome"]["reason"], "inspection_failed")
                self.assertEqual(trace["inspection"]["evidence_path"], result.evidence_path)
                self.assertEqual(adapter.calls[-4:], ["return_home", "land", "shutdown", "disconnect"])
                self.assertTrue(trace["cleanup"]["completed"])
                self.assertIn("[REVIEW REQUEST]", output)
                self.assertNotIn("[PASS]", output)

    def test_cleanup_errors_are_recorded_and_prevent_pass(self):
        for operation in ("return_home", "land", "shutdown", "disconnect"):
            with self.subTest(operation=operation):
                adapter, trace, output, error = self.run_flow(self.result("positive"), (operation,))
                self.assertIsInstance(error, RuntimeError)
                self.assertFalse(trace["cleanup"]["completed"])
                self.assertEqual(len(trace["cleanup"]["errors"]), 1)
                self.assertEqual(trace["outcome"]["reason"], "smoke_observed")
                self.assertIn("land", adapter.calls)
                self.assertIn("disconnect", adapter.calls)
                self.assertEqual("shutdown" in adapter.calls, operation != "land")
                self.assertNotIn("[PASS]", output)

    def test_cleanup_failure_preserves_primary_inspection_failure(self):
        result = self.result("perception_failure")
        _, trace, _, error = self.run_flow(result, ("land", "disconnect"))
        self.assertIn(result.error, str(error))
        self.assertEqual(len(trace["cleanup"]["errors"]), 2)
        self.assertIn(result.error, trace["execution_error"])

    def test_setup_failure_does_not_invent_inspection_or_outcome(self):
        adapter, trace, output, error = self.run_flow(self.result("positive"), ("connect",))
        self.assertIn("connect", str(error))
        self.assertIsNone(trace["inspection"])
        self.assertIsNone(trace["outcome"])
        self.assertEqual(adapter.calls, ["connect", "disconnect"])
        self.assertNotIn("[PASS]", output)

    def test_dispatch_failure_does_not_invent_observation(self):
        adapter, trace, _, error = self.run_flow(self.result("positive"), dispatch_error=True)
        self.assertIn("dispatch", str(error))
        self.assertIsNone(trace["inspection"])
        self.assertIsNone(trace["outcome"])
        self.assertEqual(adapter.calls[-4:], ["return_home", "land", "shutdown", "disconnect"])

    def test_missing_evidence_is_an_execution_failure(self):
        self.evidence.unlink()
        _, trace, output, error = self.run_flow(self.result("positive"))
        self.assertIn("evidence file is missing", str(error))
        self.assertIn("evidence file is missing", trace["execution_error"])
        self.assertNotIn("[PASS]", output)

    def test_mismatched_identifier_is_rejected_without_outcome(self):
        result = InspectionResult(
            "inspection_other", True, False, evidence_path=str(self.evidence),
        )
        _, trace, _, error = self.run_flow(result)
        self.assertIn("identifier", str(error))
        self.assertIsNone(trace["outcome"])


if __name__ == "__main__":
    print("[CONTROLLED] Synthetic fixtures only; no simulator or detector calls.", flush=True)
    unittest.main(verbosity=2)
