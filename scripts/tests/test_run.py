import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from urllib.parse import urlsplit


PROJECT_DIR = Path(__file__).resolve().parents[2]


class LauncherTests(unittest.TestCase):
    def test_startup_urls_use_localhost(self):
        # Run an isolated copy with lightweight servers, without installing
        # dependencies or taking the ports used by a running development app.
        with tempfile.TemporaryDirectory(prefix="support launcher ") as directory:
            root = Path(directory)
            shutil.copy2(PROJECT_DIR / "run.sh", root / "run.sh")
            (root / "backend/.venv/bin").mkdir(parents=True)
            (root / "frontend").mkdir()
            (root / "bin").mkdir()
            stub = f"#!{sys.executable}\n" + """
import sys
import time

if '--host' in sys.argv:
    host = sys.argv[sys.argv.index('--host') + 1]
    port = sys.argv[sys.argv.index('--port') + 1]
    print(f'Server URL: http://{host}:{port}', flush=True)
    while True:
        time.sleep(1)
"""
            for relative in ("backend/.venv/bin/python", "bin/python3", "bin/node", "bin/npm"):
                executable = root / relative
                executable.write_text(stub)
                executable.chmod(0o755)

            env = dict(os.environ, PATH=f"{root / 'bin'}{os.pathsep}{os.environ['PATH']}")
            with tempfile.TemporaryFile(mode="w+") as output:
                process = subprocess.Popen(
                    ["bash", str(root / "run.sh")],
                    cwd=root.parent,
                    env=env,
                    stdout=output,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
                try:
                    deadline = time.monotonic() + 10
                    while time.monotonic() < deadline:
                        output.seek(0)
                        log = output.read()
                        if log.count("Server URL:") == 2 or process.poll() is not None:
                            break
                        time.sleep(0.05)

                    self.assertEqual(log.count("Server URL:"), 2, log)
                    urls = re.findall(r"http://[^\s]+", log)
                    self.assertEqual(len(urls), 5, log)
                    self.assertTrue(all(urlsplit(url).hostname == "localhost" for url in urls), log)
                    for url in ("http://localhost:5173", "http://localhost:8000", "http://localhost:8000/docs"):
                        self.assertIn(url, urls)
                finally:
                    if process.poll() is None:
                        process.send_signal(signal.SIGINT)
                    process.wait(timeout=10)

                self.assertEqual(process.returncode, 130)


if __name__ == "__main__":
    unittest.main()
