"""Exercise the issue-patch publishing boundary using real temporary Git repos."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


VALIDATOR = Path(__file__).resolve().parents[1] / "validate_patch.py"
MAX_PATCH_BYTES = 2 * 1024 * 1024


class ValidatePatchTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="patch-guard-test-")
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.checkout = self.directory / "trusted checkout"
        self.checkout.mkdir()
        self.env = os.environ.copy()
        for name in list(self.env):
            if name.startswith("GIT_"):
                del self.env[name]
        self.env.update({
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_ATTR_NOSYSTEM": "1",
            "GIT_OPTIONAL_LOCKS": "0",
        })
        self.git(self.checkout, "init", "--quiet")
        self.git(self.checkout, "config", "user.name", "Patch guard test")
        self.git(self.checkout, "config", "user.email", "patch-guard@example.invalid")
        for name, content in {
            "README.md": "# Support\n",
            "backend/app.py": "answer = 1\n",
            "backend/remove me.txt": "Obsolete\n",
            "frontend/app.js": "export const answer = 1;\n",
            "docs/overview.md": "# Overview\n",
            "AGENTS.md": "Keep the quality gates.\n",
            "backend/.env": "EXAMPLE=fixture-only\n",
        }.items():
            self.write(self.checkout, name, content)
        self.git(self.checkout, "add", ".")
        self.git(self.checkout, "commit", "--quiet", "-m", "Fixture")
        self.sequence = 0

    def git(self, repo, *arguments):
        return subprocess.run(
            ["git", "-c", f"core.hooksPath={os.devnull}", "-c", "commit.gpgsign=false", *arguments],
            cwd=repo, env=self.env, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        ).stdout

    @staticmethod
    def write(repo, name, content):
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content.encode() if isinstance(content, str) else content)

    def make_patch(self, modify, stage_worktree=True):
        self.sequence += 1
        source = self.directory / f"patch source {self.sequence}"
        self.git(self.directory, "clone", "--quiet", "--no-local", str(self.checkout), str(source))
        modify(source)
        if stage_worktree:
            self.git(source, "add", "--all", "--force")
        return self.git(source, "diff", "--cached", "--binary", "--no-ext-diff", "--no-textconv", "HEAD")

    def snapshot(self):
        # Include .git: neither staged state nor object storage may be changed.
        return {
            str(path.relative_to(self.checkout)): (
                path.lstat().st_mode,
                os.readlink(path) if path.is_symlink() else path.read_bytes(),
            )
            for path in self.checkout.rglob("*")
            if path.is_symlink() or path.is_file()
        }

    def validate(self, patch, accepted, message=None):
        patch_path = self.directory / "proposed.patch"
        patch_path.write_bytes(patch)
        before = self.snapshot()
        result = subprocess.run(
            [sys.executable, str(VALIDATOR), str(patch_path)],
            cwd=self.checkout, env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, check=False,
        )
        self.assertEqual(self.snapshot(), before, "Validator changed the real repository")
        self.assertEqual(result.returncode, 0 if accepted else 1, result.stdout + result.stderr)
        if message:
            self.assertIn(message, result.stdout + result.stderr)
        return result

    def test_accepts_modification_new_regression_test_and_deletion_with_spaces(self):
        def modify(repo):
            self.write(repo, "backend/app.py", "answer = 2\n")
            self.write(repo, "frontend/tests/new test.js", "test('regression', () => {});\n")
            self.write(repo, "docs/overview.md", "# Updated overview\n")
            self.write(repo, "README.md", "# Updated support\n")
            (repo / "backend/remove me.txt").unlink()

        self.validate(self.make_patch(modify), True, "5 changed file(s)")

    def test_accepts_git_binary_patch(self):
        patch = self.make_patch(lambda repo: self.write(repo, "frontend/assets/fixture.bin", bytes(range(256))))
        self.assertIn(b"GIT binary patch", patch)
        self.validate(patch, True)

    def test_rejects_protected_and_credential_paths_at_any_depth(self):
        for name in (
            ".github/workflows/issue.yml", ".gitlab/merge_request_templates/Default.md",
            ".gitlab-ci.yml", "scripts/run.py", "AGENTS.md", "backend/AGENTS.md",
            "docs/nested/AgEnTs.Md", ".agents/policy.md", ".codex/config.toml",
            ".gitignore", ".gitattributes", ".gitmodules", ".env", ".env.local",
            "frontend/.env.production", "backend/nested/.github/workflows/ci.yml",
            "docs/.codex/config.toml", "docs/CODEOWNERS", "backend/credentials.json",
            "backend/secrets/config.json", "backend/service-account.json", "frontend/private.key",
            "docs/id_ed25519", "backend/certificate.PEM", "other/application.py",
        ):
            with self.subTest(path=name):
                patch = self.make_patch(lambda repo: self.write(repo, name, "Changed\n"))
                self.validate(patch, False)

    def test_rejects_deleting_a_secret_or_policy_file(self):
        for name in ("backend/.env", "AGENTS.md"):
            with self.subTest(path=name):
                patch = self.make_patch(lambda repo: (repo / name).unlink())
                self.validate(patch, False)

    def test_rejects_renaming_a_protected_file_into_an_allowed_path(self):
        patch = self.make_patch(lambda repo: (repo / "AGENTS.md").rename(repo / "docs/guide.md"))
        self.validate(patch, False)

    def test_rejects_symlink_creation_and_type_change(self):
        for name in ("backend/new-link", "backend/app.py"):
            with self.subTest(path=name):
                def modify(repo):
                    path = repo / name
                    if path.exists():
                        path.unlink()
                    path.symlink_to("../.github/workflows/issue.yml")

                self.validate(self.make_patch(modify), False, "Symlink and submodule")

    def test_rejects_symlink_deletion(self):
        (self.checkout / "backend/existing-link").symlink_to("app.py")
        self.git(self.checkout, "add", "backend/existing-link")
        self.git(self.checkout, "commit", "--quiet", "-m", "Existing symlink fixture")
        patch = self.make_patch(lambda repo: (repo / "backend/existing-link").unlink())
        self.validate(patch, False, "Symlink and submodule")

    def test_rejects_submodule_creation(self):
        def modify(repo):
            commit = self.git(repo, "rev-parse", "HEAD").decode().strip()
            self.git(repo, "update-index", "--add", "--cacheinfo", f"160000,{commit},backend/dependency")

        self.validate(self.make_patch(modify, stage_worktree=False), False, "Symlink and submodule")

    def test_rejects_submodule_deletion(self):
        commit = self.git(self.checkout, "rev-parse", "HEAD").decode().strip()
        self.git(self.checkout, "update-index", "--add", "--cacheinfo", f"160000,{commit},backend/dependency")
        self.git(self.checkout, "commit", "--quiet", "-m", "Existing submodule fixture")
        patch = self.make_patch(
            lambda repo: self.git(repo, "update-index", "--force-remove", "backend/dependency"),
            stage_worktree=False,
        )
        self.validate(patch, False, "Symlink and submodule")

    def test_rejects_traversal_absolute_and_ambiguous_paths(self):
        for name in ("backend/../../escape", "/tmp/codex-patch-escape", "backend/../AGENTS.md", "backend/.git/config", "backend\\escape"):
            with self.subTest(path=name):
                patch = (
                    f"diff --git a/{name} b/{name}\nnew file mode 100644\n"
                    f"--- /dev/null\n+++ b/{name}\n@@ -0,0 +1 @@\n+unsafe\n"
                ).encode()
                self.validate(patch, False)
        self.assertFalse((self.directory / "escape").exists())

    def test_rejects_control_characters_in_filenames(self):
        patch = self.make_patch(lambda repo: self.write(repo, "docs/line\nbreak.md", "Unsafe\n"))
        self.validate(patch, False, "Unsafe path")

    def test_rejects_empty_invalid_and_nonapplicable_patches(self):
        for patch in (b"", b" \n\t", b"This is not a diff.\n", b"diff --git a/backend/app.py b/backend/app.py\n"):
            with self.subTest(patch=patch):
                self.validate(patch, False)
        patch = self.make_patch(lambda repo: self.write(repo, "backend/app.py", "answer = 2\n"))
        self.validate(patch.replace(b"-answer = 1", b"-answer = 99"), False)

    def test_rejects_oversized_patch(self):
        self.validate(b"x" * (MAX_PATCH_BYTES + 1), False, "exceeds 2097152 bytes")

    def test_rejects_too_many_changed_files(self):
        def modify(repo):
            for index in range(101):
                self.write(repo, f"docs/page-{index}.md", "New\n")

        self.validate(self.make_patch(modify), False, "exceeds 100 changed files")

    def test_validation_uses_head_without_touching_existing_staged_or_worktree_changes(self):
        patch = self.make_patch(lambda repo: self.write(repo, "backend/app.py", "answer = 2\n"))
        self.write(self.checkout, "backend/app.py", "answer = 3\n")
        self.git(self.checkout, "add", "backend/app.py")
        self.write(self.checkout, "backend/app.py", "answer = 4\n")
        self.write(self.checkout, "docs/untracked.md", "Keep me\n")
        self.validate(patch, True)


if __name__ == "__main__":
    unittest.main()
