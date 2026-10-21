"""Test the Codex account boundary without changing runner service permissions."""

import importlib.util
import os
from pathlib import Path
import pwd
import socket
import stat
import subprocess
import sys
import tempfile
import tomllib
import unittest
from unittest import mock


SPEC = importlib.util.spec_from_file_location(
    "prepare_codex_runner", Path(__file__).resolve().parents[1] / "prepare_codex_runner.py"
)
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


class RunnerBoundaryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="codex-runner-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.workspace = self.root / "checkout"
        self.workspace.mkdir()
        for filename in (
            ".git/config", ".github/workflows/review.yml", "scripts/check.py",
            "AGENTS.md", "README.md", "backend/app.py", "frontend/app.js", "docs/guide.md",
        ):
            path = self.workspace / filename
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("fixture\n")

    def test_implementation_grants_only_application_tree_writes_and_keeps_executable_bits(self):
        (self.workspace / "backend/app.py").chmod(0o755)
        plan, directories = runner.permission_plan(self.workspace, "implement", os.getuid())
        permissions = {str(path.relative_to(self.workspace)): mode for mode, paths in plan.items() for path in paths}
        self.assertEqual(permissions["."], "r-x")
        for path in (".git/config", ".github/workflows/review.yml", "scripts/check.py", "AGENTS.md"):
            self.assertEqual(permissions[path], "r--", path)
        self.assertEqual(permissions["backend/app.py"], "rwx")
        for path in ("README.md", "frontend/app.js", "docs/guide.md"):
            self.assertEqual(permissions[path], "rw-", path)
        self.assertEqual(set(directories), {self.workspace / path for path in ("backend", "frontend", "docs")})

    def test_review_has_no_writable_entries_or_inheritable_write_grants(self):
        plan, directories = runner.permission_plan(self.workspace, "review", os.getuid())
        self.assertFalse(plan["rw-"] or plan["rwx"] or directories)
        self.assertIn(self.workspace / "frontend/app.js", plan["r--"])

    def test_physical_traversal_does_not_touch_symlink_targets_or_loop(self):
        outside = self.root / "outside"
        outside.mkdir()
        target = outside / "service-fixture"
        target.write_text("unrelated service state")
        target.chmod(0o666)
        before = target.stat()
        (self.workspace / "backend/external").symlink_to(outside, target_is_directory=True)
        (self.workspace / "frontend/loop").symlink_to(self.workspace, target_is_directory=True)
        (self.workspace / "docs/external-file").symlink_to(target)
        visited = {path for path, _ in runner.physical_tree(self.workspace)}
        self.assertNotIn(target, visited)
        self.assertNotIn(self.workspace / "backend/external", visited)
        self.assertNotIn(self.workspace / "docs/external-file", visited)
        self.assertEqual(target.stat().st_mode, before.st_mode)
        self.assertEqual(target.read_text(), "unrelated service state")

    def test_hardlinks_fail_before_acl_mutations_can_reach_an_external_inode(self):
        os.link(self.workspace / "backend/app.py", self.root / "external-hardlink")
        with self.assertRaisesRegex(runner.RunnerSetupError, "Hardlinked"):
            runner.permission_plan(self.workspace, "implement", os.getuid())

    def test_paths_reject_symlink_ancestors_and_control_characters(self):
        (self.root / "alias").symlink_to(self.workspace, target_is_directory=True)
        with self.assertRaisesRegex(runner.RunnerSetupError, "Symlink"):
            runner.physical_path(self.root / "alias/backend")
        for value in ("relative/path", str(self.root / "../escape"), str(self.root / "line\nbreak")):
            with self.subTest(value=value), self.assertRaises(runner.RunnerSetupError):
                runner.clean_path(value)

    def test_tool_path_excludes_checkout_aliases_and_writable_ancestors(self):
        toolchain = self.root / 'installed tools "quoted"'
        unsafe_parent = self.root / "writable"
        unsafe_tools = unsafe_parent / "bin"
        toolchain.mkdir()
        unsafe_tools.mkdir(parents=True)
        alias = self.root / "workspace-alias"
        alias.symlink_to(self.workspace, target_is_directory=True)
        value = os.pathsep.join(("", ".", str(toolchain), str(alias), str(unsafe_tools), str(toolchain)))
        path = runner.trusted_path(
            value, [self.workspace], lambda paths: [entry == unsafe_parent for entry in paths],
        )
        self.assertEqual(path, str(toolchain))
        with self.assertRaisesRegex(runner.RunnerSetupError, "PATH has no"):
            runner.trusted_path(str(unsafe_tools), [], lambda paths: [True] * len(paths))

    def test_config_round_trips_tool_path_and_runtime_files_without_toml_injection(self):
        tools = '/opt/Python/bin:/opt/tools "quoted"/bin:/opt/emoji-🚀/bin'
        evidence = self.root / 'scratch "quoted"/evidence.txt'
        issue = self.root / 'issue\\data.json'
        config = tomllib.loads(runner.codex_config(tools, evidence, issue))
        self.assertFalse(config["allow_login_shell"])
        self.assertEqual(config["shell_environment_policy"]["set"], {
            "PATH": tools, "TMPDIR": str(evidence.parent),
            "EVIDENCE_FILE": str(evidence), "CODEX_ISSUE_FILE": str(issue),
        })
        self.assertNotIn("CODEX_ISSUE_FILE", tomllib.loads(runner.codex_config(tools, evidence))["shell_environment_policy"]["set"])

    def test_unsafe_runtime_paths_and_reused_identity_fail_before_any_sudo_mutation(self):
        with (
            mock.patch.object(runner.sys, "platform", "linux"),
            mock.patch.object(runner.os, "geteuid", return_value=1001),
            mock.patch.object(runner.shutil, "which", return_value="/usr/bin/tool"),
            mock.patch.object(runner, "sudo") as privileged,
        ):
            for runtime, temporary in (
                (self.workspace / "runtime", self.workspace),
                (self.root / "nested/runtime", self.root),
                (self.workspace, self.root),
            ):
                with self.subTest(runtime=runtime), self.assertRaises(runner.RunnerSetupError):
                    runner.prepare("implement", self.workspace, runtime, temporary, "123")
            with mock.patch.object(runner.pwd, "getpwnam", return_value=object()):
                with self.assertRaisesRegex(runner.RunnerSetupError, "existing Codex account"):
                    runner.prepare("implement", self.workspace, self.root / "runtime", self.root, "123")
            privileged.assert_not_called()


@unittest.skipUnless(
    os.environ.get("CODEX_RUNNER_INTEGRATION") == "1" and sys.platform.startswith("linux"),
    "Linux account/ACL integration requires CODEX_RUNNER_INTEGRATION=1 on a disposable runner",
)
class LinuxRunnerIntegrationTests(unittest.TestCase):
    sequence = 0

    def command(self, *arguments, **kwargs):
        return subprocess.run(list(map(str, arguments)), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)

    def setUp(self):
        self.assertNotEqual(os.geteuid(), 0, "Run integration tests as the normal sudo-capable runner, not root")
        self.command("/usr/bin/sudo", "-n", "true", check=True)
        self.command("setfacl", "--version", check=True)
        temporary = tempfile.TemporaryDirectory(prefix="codex-linux-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.workspace = self.root / "checkout"
        self.workspace.mkdir()
        self.runner_temp = self.root / "runner-temp"
        self.runner_temp.mkdir()
        self.runtime = self.runner_temp / "codex-runtime"
        type(self).sequence += 1
        self.username = f"codex-test-{os.getpid()}-{self.sequence}"
        ancestors = sorted(set(self.workspace.parents) | {self.runner_temp, *self.runner_temp.parents})
        original_acls = self.command("getfacl", "--absolute-names", "--numeric", "--", *ancestors, check=True).stdout
        self.addCleanup(lambda: self.command("sudo", "-n", "setfacl", "--restore=-", input=original_acls, check=True))
        self.addCleanup(self.remove_account)
        self.command("git", "init", "--quiet", self.workspace, check=True)
        self.command("git", "-C", self.workspace, "config", "user.email", "runner@example.invalid", check=True)
        self.command("git", "-C", self.workspace, "config", "user.name", "Runner fixture", check=True)
        for filename in ("README.md", "backend/app.py", "frontend/app.js", "docs/guide.md", ".github/review.yml", "scripts/check.py"):
            path = self.workspace / filename
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("fixture\n")
        self.command("git", "-C", self.workspace, "add", ".", check=True)
        self.command("git", "-C", self.workspace, "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false", "commit", "--quiet", "-m", "Fixture", check=True)
        # Named user ACLs must override even overly permissive inherited modes.
        self.workspace.chmod(0o777)
        (self.workspace / ".git").chmod(0o777)
        (self.workspace / ".git/config").chmod(0o666)
        (self.workspace / ".github/review.yml").chmod(0o666)
        self.outside = self.root / "service-state"
        self.outside.write_text("unrelated")
        self.outside.chmod(0o666)
        (self.workspace / "frontend/external-link").symlink_to(self.outside)
        self.service_socket = self.root / "service.sock"
        connection = socket.socket(socket.AF_UNIX)
        connection.bind(str(self.service_socket))
        self.addCleanup(connection.close)
        self.service_socket.chmod(0o666)
        self.service_modes = [path.stat().st_mode for path in (self.outside, self.service_socket)]
        self.service_acls = self.command("getfacl", "--absolute-names", "--", self.outside, self.service_socket, check=True).stdout

    def remove_account(self):
        try:
            pwd.getpwnam(self.username)
        except KeyError:
            return
        self.command("sudo", "-n", "userdel", "--remove", self.username, check=True)

    def worker(self, script, *arguments):
        return runner.as_worker(self.username, "/usr/bin/python3", "-I", "-c", script, *arguments, check=False)

    def assert_services_unchanged(self):
        self.assertEqual([path.stat().st_mode for path in (self.outside, self.service_socket)], self.service_modes)
        self.assertEqual(self.outside.read_text(), "unrelated")
        self.assertEqual(self.command("getfacl", "--absolute-names", "--", self.outside, self.service_socket, check=True).stdout, self.service_acls)

    def test_implementation_can_edit_app_but_not_git_inputs_or_summary_path(self):
        issue = self.runner_temp / "original-issue.json"
        issue.write_text('{"body":"fixture"}')
        outputs = runner.prepare("implement", self.workspace, self.runtime, self.runner_temp, "12345", issue, username=self.username)
        account = pwd.getpwnam(self.username)
        self.assertEqual(set(os.getgrouplist(self.username, account.pw_gid)), {account.pw_gid})
        writer = "from pathlib import Path; import sys; Path(sys.argv[1]).write_text('changed')"
        for path in (self.workspace / "backend/app.py", self.workspace / "frontend/new-test.js", self.workspace / "docs/guide.md", self.workspace / "README.md"):
            result = self.worker(writer, path)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(path.read_text(), "changed", "Runner must be able to capture worker-created files")
        for path in (self.workspace / ".git/config", self.workspace / ".github/review.yml", self.workspace / "scripts/check.py", self.workspace / "new-root-file", Path(outputs["issue_file"])):
            result = self.worker(writer, path)
            self.assertNotEqual(result.returncode, 0, str(path))
        summary = Path(outputs["summary_file"])
        self.assertEqual(self.worker(writer, summary).returncode, 0)
        self.assertEqual(summary.read_text(), "changed")
        self.assertEqual(summary.stat().st_uid, os.getuid())
        self.assertTrue(stat.S_ISREG(summary.lstat().st_mode))
        self.assertNotEqual(self.worker("import os,sys; os.unlink(sys.argv[1])", summary).returncode, 0)
        home = Path(account.pw_dir)
        proxy_info = home / ".codex/12345.json"
        self.assertEqual(proxy_info.stat().st_uid, os.getuid())
        proxy_info.write_text('{"fixture":"proxy can write this as runner"}')
        config = tomllib.loads((home / ".codex/config.toml").read_text())
        environment = config["shell_environment_policy"]["set"]
        self.assertEqual(environment["CODEX_ISSUE_FILE"], outputs["issue_file"])
        self.assertEqual(self.worker(writer, environment["EVIDENCE_FILE"]).returncode, 0)
        temporary = self.worker(
            "import os,sys,tempfile; os.environ['TMPDIR']=sys.argv[1]; "
            "f=tempfile.NamedTemporaryFile(); print(f.name)", environment["TMPDIR"],
        )
        self.assertEqual(temporary.returncode, 0, temporary.stderr)
        self.assertEqual(Path(temporary.stdout.strip()).parent, self.runtime / "scratch")
        self.assertFalse(config["allow_login_shell"])
        safe = runner.as_worker(self.username, "/usr/bin/git", "config", "--global", "--get-all", "safe.directory")
        self.assertEqual(safe.stdout.strip(), str(self.workspace))
        self.assert_services_unchanged()

    def test_review_can_read_and_emit_summary_but_cannot_modify_any_checkout_file(self):
        outputs = runner.prepare("review", self.workspace, self.runtime, self.runner_temp, "12345", username=self.username)
        read = self.worker("from pathlib import Path; import sys; print(Path(sys.argv[1]).read_text())", self.workspace / "backend/app.py")
        self.assertEqual(read.returncode, 0, read.stderr)
        self.assertEqual(read.stdout.strip(), "fixture")
        for path in (self.workspace / "backend/app.py", self.workspace / "frontend/new-test.js", self.workspace / "README.md"):
            result = self.worker("from pathlib import Path; import sys; Path(sys.argv[1]).write_text('not allowed')", path)
            self.assertNotEqual(result.returncode, 0, str(path))
        self.assertEqual(self.worker("from pathlib import Path; import sys; Path(sys.argv[1]).write_text('review')", outputs["summary_file"]).returncode, 0)
        self.assertNotIn("issue_file", outputs)
        self.assert_services_unchanged()


if __name__ == "__main__":
    unittest.main()
