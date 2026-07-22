import io
import json
import os
import asyncio
import subprocess
import tempfile
import threading
import time
import unittest
import zipfile
from pathlib import Path
from unittest.mock import Mock, patch

from fastapi import HTTPException
from fastapi import Response

import convert_cli
import web.app as web_app
from converter.common.names import MAX_MODEL_NAME_LENGTH, sanitize_model_name


class UploadStub:
    def __init__(self, data: bytes) -> None:
        self.file = io.BytesIO(data)


class RequestStub:
    def __init__(self, token: str = "") -> None:
        self.headers = {"authorization": f"Bearer {token}"} if token else {}
        self.cookies = {}
        self.url = Mock(scheme="http")
        self.client = Mock(host="127.0.0.1")


class SafetyTests(unittest.TestCase):
    def test_upload_limit_is_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "upload.bin"
            with self.assertRaises(HTTPException) as raised:
                web_app.save_upload(UploadStub(b"1234"), path, max_bytes=3, label="model")
            self.assertEqual(raised.exception.status_code, 413)

    def test_request_body_limit_rejects_chunked_upload(self) -> None:
        called = False

        async def inner_app(scope, receive, send) -> None:
            nonlocal called
            called = True
            while True:
                message = await receive()
                if not message.get("more_body"):
                    break

        middleware = web_app.BodySizeLimitMiddleware(inner_app, max_bytes=3)
        messages = iter(
            [
                {"type": "http.request", "body": b"12", "more_body": True},
                {"type": "http.request", "body": b"34", "more_body": False},
            ]
        )
        sent = []

        async def receive():
            return next(messages)

        async def send(message) -> None:
            sent.append(message)

        scope = {"type": "http", "method": "POST", "path": "/api/jobs", "headers": []}
        asyncio.run(middleware(scope, receive, send))
        self.assertTrue(called)
        self.assertEqual(sent[0]["status"], 413)

    def test_zip_path_traversal_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "bad.zip"
            with zipfile.ZipFile(archive, "w") as zf:
                zf.writestr("../escape.txt", "x")
            with self.assertRaisesRegex(ValueError, "unsafe zip entry"):
                convert_cli.extract_zip_safely(archive, root / "out")

    def test_zip_entry_limit_is_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "many.zip"
            with zipfile.ZipFile(archive, "w") as zf:
                zf.writestr("a.txt", "a")
                zf.writestr("b.txt", "b")
            with patch.object(convert_cli, "MAX_ZIP_ENTRIES", 1):
                with self.assertRaisesRegex(ValueError, "too many entries"):
                    convert_cli.extract_zip_safely(archive, root / "out")

    def test_onnx_input_size_overrides_requested_size(self) -> None:
        import onnx
        from onnx import TensorProto, helper

        with tempfile.TemporaryDirectory() as tmp:
            model_path = Path(tmp) / "model.onnx"
            graph = helper.make_graph(
                [helper.make_node("Identity", ["images"], ["output"])],
                "shape-test",
                [helper.make_tensor_value_info("images", TensorProto.FLOAT, [1, 3, 224, 320])],
                [helper.make_tensor_value_info("output", TensorProto.FLOAT, [1, 3, 224, 320])],
            )
            onnx.save(helper.make_model(graph), model_path)
            self.assertEqual(convert_cli.read_onnx_input_hw(model_path, fallback=(480, 640)), (224, 320))

    def test_pt_loading_enables_restricted_mode(self) -> None:
        with patch.dict(os.environ, {"ULTRALYTICS_SAFE_LOAD": "0"}, clear=False):
            os.environ.pop("MAIX_ALLOW_UNSAFE_PT", None)
            convert_cli.configure_safe_pt_loading()
            self.assertEqual(os.environ["ULTRALYTICS_SAFE_LOAD"], "1")

    def test_converter_runtime_directories_stay_inside_job(self) -> None:
        previous_tempdir = tempfile.tempdir
        with tempfile.TemporaryDirectory() as tmp:
            job_dir = Path(tmp) / "project" / "jobs" / "job-1"
            job_dir.mkdir(parents=True)
            try:
                with patch.dict(os.environ, {}, clear=False):
                    convert_cli.configure_runtime_directories(job_dir)
                    for name in ["YOLO_CONFIG_DIR", "TORCH_HOME", "MPLCONFIGDIR", "HF_HOME", "TMP"]:
                        configured = Path(os.environ[name]).resolve()
                        self.assertIn(job_dir.resolve(), configured.parents)
            finally:
                tempfile.tempdir = previous_tempdir

    def test_web_runtime_directories_use_project_root(self) -> None:
        self.assertEqual(web_app.JOBS_DIR, web_app.BASE_DIR / "jobs")
        self.assertIn(web_app.BASE_DIR, web_app.TEMP_DIR.parents)

    def test_model_names_are_windows_safe_and_bounded(self) -> None:
        self.assertEqual(sanitize_model_name("CON"), "model_CON")
        self.assertEqual(sanitize_model_name("nul.weights"), "model_nul.weights")
        self.assertEqual(sanitize_model_name("normal model"), "normal_model")
        self.assertLessEqual(len(sanitize_model_name("x" * 200)), MAX_MODEL_NAME_LENGTH)

    def test_process_group_options_cover_linux_and_windows(self) -> None:
        with patch.object(web_app.os, "name", "posix"):
            self.assertEqual(web_app.process_group_options(), {"start_new_session": True})
        with (
            patch.object(web_app.os, "name", "nt"),
            patch.object(web_app.subprocess, "CREATE_NEW_PROCESS_GROUP", 512, create=True),
        ):
            self.assertEqual(web_app.process_group_options(), {"creationflags": 512})

    def test_remote_api_token_session(self) -> None:
        with patch.object(web_app, "API_TOKEN", "test-secret"):
            with self.assertRaises(HTTPException) as raised:
                web_app.create_api_session(RequestStub("wrong"), Response())
            self.assertEqual(raised.exception.status_code, 401)

            response = Response()
            result = web_app.create_api_session(RequestStub("test-secret"), response)
            self.assertTrue(result["authenticated"])
            self.assertIn("maix_api_token=", response.headers["set-cookie"])
            self.assertTrue(web_app.request_has_valid_token(RequestStub("test-secret")))
            self.assertFalse(web_app.request_has_valid_token(RequestStub("wrong")))
            self.assertTrue(web_app.is_loopback_client("127.0.0.1"))
            self.assertFalse(web_app.is_loopback_client("192.168.1.10"))

    def test_startup_reconciles_interrupted_job(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            jobs_dir = Path(tmp)
            job_dir = jobs_dir / "20260101_000000_test_maixcam2_yolo11"
            job_dir.mkdir()
            (job_dir / "job.json").write_text(
                json.dumps({"status": "running", "stage": "exporting", "job_id": job_dir.name}),
                encoding="utf-8",
            )
            with (
                patch.object(web_app, "JOBS_DIR", jobs_dir),
                patch.object(web_app, "remove_job_container", return_value=""),
            ):
                web_app.reconcile_interrupted_jobs()
            job = json.loads((job_dir / "job.json").read_text(encoding="utf-8"))
            self.assertEqual(job["status"], "cancelled")
            self.assertIn("server restarted", job["error"])

    def test_job_executor_queues_above_concurrency_limit(self) -> None:
        release_first = threading.Event()
        second_started = threading.Event()

        def first_job() -> None:
            release_first.wait(2)

        def second_job() -> None:
            second_started.set()

        with patch.object(web_app, "MAX_CONCURRENT_JOBS", 1):
            web_app.job_executor = None
            executor = web_app.ensure_job_executor()
            try:
                first = executor.submit(first_job)
                second = executor.submit(second_job)
                self.assertFalse(second_started.wait(0.1))
                release_first.set()
                first.result(timeout=2)
                second.result(timeout=2)
                self.assertTrue(second_started.is_set())
            finally:
                release_first.set()
                executor.shutdown(wait=True)
                web_app.job_executor = None

    def test_docker_cleanup_failure_is_reported(self) -> None:
        result = Mock(returncode=1, stdout="permission denied")
        with patch.object(subprocess, "run", return_value=result):
            warning = web_app.remove_job_container(Path("/tmp/job"), expect_container=True)
        self.assertIn("permission denied", warning)

    def test_windows_recovery_verifies_command_before_taskkill(self) -> None:
        job_dir = Path("maix_converter_platform/jobs/job-1")
        with (
            patch.object(web_app.os, "name", "nt"),
            patch.object(
                web_app,
                "read_process_command_line",
                return_value="python convert_cli.py --job-dir maix_converter_platform/jobs/job-1",
            ),
            patch.object(web_app, "run_taskkill") as taskkill,
        ):
            web_app.terminate_recorded_process(job_dir, {"runner_pid": 1234})
        taskkill.assert_called_once_with(1234, force=True)

    def test_windows_recovery_does_not_kill_unrelated_pid(self) -> None:
        job_dir = Path("maix_converter_platform/jobs/job-1")
        with (
            patch.object(web_app.os, "name", "nt"),
            patch.object(web_app, "read_process_command_line", return_value="python unrelated.py"),
            patch.object(web_app, "run_taskkill") as taskkill,
        ):
            web_app.terminate_recorded_process(job_dir, {"runner_pid": 1234})
        taskkill.assert_not_called()

    @unittest.skipIf(os.name == "nt", "POSIX process groups are tested on Linux/macOS")
    def test_process_tree_is_terminated(self) -> None:
        process = subprocess.Popen(["bash", "-c", "sleep 30 & wait"], start_new_session=True)
        try:
            time.sleep(0.1)
            web_app.terminate_process_tree(process)
            with self.assertRaises(ProcessLookupError):
                os.killpg(process.pid, 0)
        finally:
            if process.poll() is None:
                process.kill()


if __name__ == "__main__":
    unittest.main()
