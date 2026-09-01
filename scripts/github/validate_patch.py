#!/usr/bin/env python3
"""Validate an untrusted issue patch against HEAD without applying it locally.

Only application code, ordinary documentation, and README.md may change. This
is a path/mode boundary, not a substitute for reviewing the generated code.
"""

import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile


MAX_PATCH_BYTES = 2 * 1024 * 1024
MAX_CHANGED_FILES = 100
GIT_TIMEOUT_SECONDS = 30
ALLOWED_ROOTS = {"backend", "frontend", "docs"}
ALLOWED_MODES = {b"000000", b"100644", b"100755"}
CREDENTIAL_SUFFIXES = {".pem", ".key", ".p12", ".pfx", ".jks", ".keystore"}


class PatchValidationError(Exception):
    """The patch cannot safely cross the automation's publishing boundary."""


def run_git(arguments, env, cwd=None, input_bytes=None):
    try:
        result = subprocess.run(
            [
                "git", "--no-pager", "-c", "core.fsmonitor=false",
                "-c", f"core.hooksPath={os.devnull}", *arguments,
            ],
            cwd=cwd,
            env=env,
            input=input_bytes,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=GIT_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise PatchValidationError("Git validation timed out") from exc
    if result.returncode:
        detail = result.stderr.decode("utf-8", errors="replace").strip()[:500]
        raise PatchValidationError(f"git {arguments[0]} failed: {detail!r}")
    return result.stdout


def validate_path(raw_path):
    try:
        path = raw_path.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PatchValidationError("Filenames must be valid UTF-8") from exc
    parts = path.split("/")
    if (
        "\\" in path
        or any(ord(character) < 32 or ord(character) == 127 for character in path)
        or any(part in {"", ".", ".."} for part in parts)
    ):
        raise PatchValidationError(f"Unsafe path: {path!r}")
    if path != "README.md" and not (len(parts) > 1 and parts[0] in ALLOWED_ROOTS):
        raise PatchValidationError(f"Path is outside the application allowlist: {path!r}")
    for part in parts:
        name = part.casefold()
        if name.startswith(".") or name in {"agents.md", "codeowners"}:
            raise PatchValidationError(f"Protected control or hidden path: {path!r}")
        if (
            name in {"credentials", "secrets", "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519"}
            or name.startswith(("credentials.", "secrets.", "service-account", "service_account", "client_secret"))
            or Path(name).suffix in CREDENTIAL_SUFFIXES
        ):
            raise PatchValidationError(f"Credential-like path: {path!r}")


def validate_patch(patch_path):
    with open(patch_path, "rb") as patch_file:
        patch = patch_file.read(MAX_PATCH_BYTES + 1)
    if not patch.strip():
        raise PatchValidationError("Patch is empty")
    if len(patch) > MAX_PATCH_BYTES:
        raise PatchValidationError(f"Patch exceeds {MAX_PATCH_BYTES} bytes")

    env = os.environ.copy()
    env["GIT_OPTIONAL_LOCKS"] = "0"
    root = os.fsdecode(run_git(["rev-parse", "--show-toplevel"], env).rstrip(b"\n"))
    object_directory = run_git(
        ["rev-parse", "--path-format=absolute", "--git-path", "objects"], env, root
    ).rstrip(b"\n")

    with tempfile.TemporaryDirectory(prefix="codex-patch-") as temporary:
        # Keep new blobs out of the real object database as well as the index.
        objects = Path(temporary) / "objects"
        (objects / "info").mkdir(parents=True)
        (objects / "info" / "alternates").write_bytes(object_directory + b"\n")
        env["GIT_INDEX_FILE"] = str(Path(temporary) / "index")
        env["GIT_OBJECT_DIRECTORY"] = str(objects)
        run_git(["read-tree", "HEAD"], env, root)
        run_git(["apply", "--cached", "--binary", "--whitespace=nowarn", "-"], env, root, patch)
        diff = run_git(
            ["diff", "--cached", "--raw", "-z", "--no-renames", "--no-ext-diff", "--no-textconv", "HEAD", "--"],
            env, root,
        )

    if not diff:
        raise PatchValidationError("Patch makes no changes to HEAD")
    records = diff.split(b"\0")
    if records[-1] != b"" or len(records) % 2 != 1:
        raise PatchValidationError("Unexpected Git diff output")
    changed_files = (len(records) - 1) // 2
    if changed_files > MAX_CHANGED_FILES:
        raise PatchValidationError(f"Patch exceeds {MAX_CHANGED_FILES} changed files")
    for offset in range(0, len(records) - 1, 2):
        metadata = records[offset].split()
        if len(metadata) != 5 or not metadata[0].startswith(b":"):
            raise PatchValidationError("Unexpected Git diff metadata")
        if metadata[0][1:] not in ALLOWED_MODES or metadata[1] not in ALLOWED_MODES:
            raise PatchValidationError("Symlink and submodule changes are not allowed")
        validate_path(records[offset + 1])
    return changed_files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("patch", help="Git binary patch to validate against this checkout's HEAD")
    arguments = parser.parse_args()
    try:
        count = validate_patch(arguments.patch)
    except (OSError, PatchValidationError) as exc:
        print(f"Patch rejected: {exc}", file=sys.stderr)
        return 1
    print(f"Patch accepted: {count} changed file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
