#!/usr/bin/env python3
"""Prepare an isolated Codex account without changing host service permissions.

Run before passing an API key to codex-action, on a fresh Linux runner. The
account may edit application files, but cannot replace Git metadata, workflow
inputs, or its output artifact path. A later clean job still validates its patch.
"""

import argparse
import grp
import json
import os
from pathlib import Path
import pwd
import re
import shutil
import stat
import subprocess
import sys
import tempfile


USERNAME = "codex-worker"
WRITABLE_ROOTS = {"backend", "frontend", "docs"}


class RunnerSetupError(Exception):
    """The runner cannot satisfy the isolation boundary."""


def clean_path(value):
    path = Path(value)
    if (
        not path.is_absolute()
        or ".." in path.parts
        or any(ord(character) < 32 or ord(character) == 127 for character in str(path))
    ):
        raise RunnerSetupError("Paths must be absolute, without traversal or control characters")
    str(path).encode("utf-8")
    return path


def physical_path(value, *, directory=True):
    """Validate every ancestor, not just the final component, without resolving links."""
    path = clean_path(value)
    for component in reversed((path, *path.parents)):
        mode = component.lstat().st_mode
        if stat.S_ISLNK(mode):
            raise RunnerSetupError(f"Symlink is not allowed in setup path: {component}")
        if component != path or directory:
            if not stat.S_ISDIR(mode):
                raise RunnerSetupError(f"Expected directory: {component}")
        elif not stat.S_ISREG(mode):
            raise RunnerSetupError(f"Expected regular file: {component}")
    return path


def within(path, parent):
    return path == parent or parent in path.parents


def physical_tree(root):
    """Skip repository links entirely: their targets must never receive an ACL."""
    pending = [root]
    while pending:
        path = pending.pop()
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode):
            continue
        if not (stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode)):
            raise RunnerSetupError(f"Special file is not allowed in checkout: {path}")
        if stat.S_ISREG(info.st_mode) and info.st_nlink != 1:
            raise RunnerSetupError(f"Hardlinked file is not allowed in checkout: {path}")
        yield path, info
        if stat.S_ISDIR(info.st_mode):
            with os.scandir(path) as entries:
                pending.extend(Path(entry.path) for entry in entries)


def permission_plan(workspace, mode, runner_uid):
    if mode not in {"implement", "review"}:
        raise RunnerSetupError("Mode must be implement or review")
    plan = {"r--": [], "r-x": [], "rw-": [], "rwx": []}
    writable_directories = []
    for path, info in physical_tree(workspace):
        if info.st_uid != runner_uid:
            raise RunnerSetupError(f"Checkout entry is not owned by the runner: {path}")
        parts = path.relative_to(workspace).parts
        writable = mode == "implement" and bool(parts) and (
            parts[0] in WRITABLE_ROOTS or parts == ("README.md",)
        )
        executable = stat.S_ISDIR(info.st_mode) or bool(info.st_mode & 0o111)
        permissions = "r" + ("w" if writable else "-") + ("x" if executable else "-")
        plan[permissions].append(path)
        if writable and stat.S_ISDIR(info.st_mode):
            writable_directories.append(path)
    return plan, writable_directories


def run(arguments, *, input_text=None, check=True):
    result = subprocess.run(
        [str(argument) for argument in arguments], input=input_text, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=60,
    )
    if check and result.returncode:
        # Do not echo arbitrary checkout filenames or inherited environment values.
        raise RunnerSetupError(f"Runner setup command failed: {Path(str(arguments[0])).name}")
    return result


def sudo(*arguments, **kwargs):
    return run(["/usr/bin/sudo", "-n", *arguments], **kwargs)


def as_worker(username, *arguments, **kwargs):
    return sudo("-H", "-u", username, "--", *arguments, **kwargs)


def set_acl(paths, specification):
    paths = list(paths)
    # Bound argv size, and never recurse through setfacl itself.
    for offset in range(0, len(paths), 100):
        sudo("setfacl", "--physical", "--modify", specification, "--", *paths[offset:offset + 100])


def worker_writable(username, paths):
    script = "import json,os,sys; print(json.dumps([os.access(p,os.W_OK) for p in sys.argv[1:]]))"
    result = as_worker(username, "/usr/bin/python3", "-I", "-c", script, *paths)
    return json.loads(result.stdout)


def trusted_path(raw_path, excluded, is_writable):
    """Retain installed toolchains, not tools replaceable by the Codex account."""
    candidates = []
    for entry in raw_path.split(os.pathsep):
        if not entry:
            continue
        try:
            path = clean_path(entry).resolve(strict=True)
        except (OSError, RunnerSetupError, UnicodeError):
            continue
        if not path.is_dir() or any(within(path, root) for root in excluded):
            continue
        if path not in candidates:
            candidates.append(path)
    # A writable ancestor allows replacing a tool directory even if it is read-only.
    checks = list(dict.fromkeys(parent for path in candidates for parent in (path, *path.parents)))
    writable = dict(zip(checks, is_writable(checks), strict=True))
    safe = [path for path in candidates if not any(writable[parent] for parent in (path, *path.parents))]
    if not safe:
        raise RunnerSetupError("PATH has no tool directories protected from the Codex account")
    return os.pathsep.join(map(str, safe))


def codex_config(path, evidence_file, issue_file=None):
    environment = {
        "PATH": path, "TMPDIR": str(Path(evidence_file).parent),
        "EVIDENCE_FILE": str(evidence_file),
    }
    if issue_file is not None:
        environment["CODEX_ISSUE_FILE"] = str(issue_file)
    # JSON strings with literal Unicode are also valid TOML basic strings.
    lines = ["allow_login_shell = false", "", "[shell_environment_policy.set]"]
    lines.extend(f"{name} = {json.dumps(value, ensure_ascii=False)}" for name, value in environment.items())
    return "\n".join(lines) + "\n"


def install_home_file(runtime, destination, content, owner, group, mode):
    with tempfile.NamedTemporaryFile(mode="w", dir=runtime, encoding="utf-8") as temporary:
        temporary.write(content)
        temporary.flush()
        sudo("install", "-o", str(owner), "-g", str(group), "-m", mode, temporary.name, destination)


def preflight(username, workspace, runtime, summary, mode):
    if as_worker(username, "/usr/bin/sudo", "-n", "true", check=False).returncode == 0:
        raise RunnerSetupError("Codex account unexpectedly has sudo access")
    as_worker(
        username, "/usr/bin/git", "-c", "core.fsmonitor=false", "-c", "core.hooksPath=/dev/null",
        "-C", workspace, "status", "--porcelain", "--untracked-files=no",
    )
    protected = [workspace, workspace / ".git", workspace / ".git/config", runtime]
    if any(worker_writable(username, protected)):
        raise RunnerSetupError("Codex can write protected checkout or runtime metadata")
    if not all(worker_writable(username, [summary, runtime / "scratch"])):
        raise RunnerSetupError("Codex cannot write its summary or scratch output")
    application = [workspace / name for name in sorted(WRITABLE_ROOTS | {"README.md"}) if (workspace / name).exists()]
    rights = worker_writable(username, application)
    if mode == "implement" and not all(rights):
        raise RunnerSetupError("Codex cannot edit the allowed application paths")
    if mode == "review" and any(rights):
        raise RunnerSetupError("Review account can modify the checkout")


def prepare(mode, workspace, runtime, runner_temp, run_id, issue_file=None, *, username=USERNAME):
    if not sys.platform.startswith("linux") or os.geteuid() == 0:
        raise RunnerSetupError("Use a normal, sudo-capable account on a fresh Linux runner")
    if not re.fullmatch(r"[a-z][a-z0-9-]{0,30}", username) or not re.fullmatch(r"[0-9]+", run_id):
        raise RunnerSetupError("Invalid account name or GITHUB_RUN_ID")
    for tool in ("/usr/bin/sudo", "/usr/bin/python3", "/usr/bin/git", "setfacl", "useradd", "install"):
        if shutil.which(tool) is None:
            raise RunnerSetupError(f"Required runner tool missing: {tool} (install the acl package for setfacl)")
    workspace = physical_path(workspace)
    physical_path(workspace / ".git")  # Linked worktrees and symlinked .git are not supported.
    runner_temp = physical_path(runner_temp)
    runtime = clean_path(runtime)
    if (
        runtime.parent != runner_temp or within(runtime, workspace)
        or within(workspace, runtime) or runtime.exists() or runtime.is_symlink()
    ):
        raise RunnerSetupError("Runtime must be a new direct child of RUNNER_TEMP, outside the checkout")
    if runner_temp.stat().st_uid != os.getuid():
        raise RunnerSetupError("RUNNER_TEMP must be owned by the runner")
    home = Path("/home") / username
    try:
        pwd.getpwnam(username)
    except KeyError:
        pass
    else:
        raise RunnerSetupError("Refusing to reuse an existing Codex account")
    try:
        grp.getgrnam(username)
    except KeyError:
        pass
    else:
        raise RunnerSetupError("Refusing to reuse an existing Codex group")
    if home.exists() or home.is_symlink():
        raise RunnerSetupError("Refusing to reuse an existing Codex home")
    issue_bytes = None
    if issue_file is not None:
        issue_file = physical_path(issue_file, directory=False)
        if not within(issue_file, runner_temp) or issue_file.stat().st_uid != os.getuid():
            raise RunnerSetupError("Issue data must be a runner-owned file under RUNNER_TEMP")
        with issue_file.open("rb") as source:
            issue_bytes = source.read(1024 * 1024 + 1)
        if len(issue_bytes) > 1024 * 1024:
            raise RunnerSetupError("Issue data exceeds 1 MiB")
    plan, writable_directories = permission_plan(workspace, mode, os.getuid())
    sudo("true")
    sudo("useradd", "--create-home", "--user-group", "--no-log-init", "--home-dir", home, "--shell", "/bin/bash", username)
    account = pwd.getpwnam(username)
    if (
        account.pw_uid in {0, os.getuid()} or account.pw_gid in {0, os.getgid()}
        or grp.getgrgid(account.pw_gid).gr_name != username
        or account.pw_dir != str(home)
        or set(os.getgrouplist(username, account.pw_gid)) != {account.pw_gid}
    ):
        raise RunnerSetupError("Codex account must have a separate UID and no supplementary groups")

    # Named-user ACLs override permissive group/other bits without rewriting any
    # service socket modes. Never chmod/chown /run or scan anything outside checkout.
    ancestors = set(workspace.parents) | {runner_temp, *runner_temp.parents}
    set_acl(sorted(ancestors), f"u:{account.pw_uid}:--x")
    for permissions, paths in plan.items():
        set_acl(paths, f"u:{account.pw_uid}:{permissions}")
    set_acl(writable_directories, f"d:u:{os.getuid()}:rwx,d:u:{account.pw_uid}:rwx")

    runtime.mkdir(mode=0o700)
    set_acl([runtime], f"u:{account.pw_uid}:r-x")
    summary = runtime / "summary.md"
    summary.touch(mode=0o600, exist_ok=False)
    set_acl([summary], f"u:{account.pw_uid}:rw-")
    issue_copy = None
    if issue_bytes is not None:
        issue_copy = runtime / "issue.json"
        issue_copy.write_bytes(issue_bytes)
        issue_copy.chmod(0o600)
        set_acl([issue_copy], f"u:{account.pw_uid}:r--")
    scratch = runtime / "scratch"
    scratch.mkdir(mode=0o700)
    sudo("chown", f"{account.pw_uid}:{account.pw_gid}", scratch)
    set_acl([scratch], f"u:{os.getuid()}:rwx,d:u:{os.getuid()}:rwx")

    codex_home = home / ".codex"
    sudo("chmod", "0700", home)
    sudo("install", "-d", "-o", str(account.pw_uid), "-g", str(account.pw_gid), "-m", "0700", codex_home)
    set_acl([home, codex_home], f"u:{os.getuid()}:r-x,d:u:{os.getuid()}:r-x")
    path = trusted_path(
        os.environ.get("PATH", os.defpath), [workspace, runtime, home],
        lambda paths: worker_writable(username, paths),
    )
    install_home_file(
        runtime, codex_home / "config.toml",
        codex_config(path, scratch / "gitlab-quality-evidence.txt", issue_copy),
        os.getuid(), os.getgid(), "0644",
    )
    # codex-action returns early for an existing .codex directory, so prepare its
    # proxy handoff file too. The action fills it as runner, then locks it as root.
    install_home_file(runtime, codex_home / f"{run_id}.json", "", os.getuid(), os.getgid(), "0600")
    as_worker(username, "/usr/bin/git", "config", "--global", "--add", "safe.directory", workspace)
    preflight(username, workspace, runtime, summary, mode)
    outputs = {"username": username, "runtime_dir": str(runtime), "summary_file": str(summary)}
    if issue_copy is not None:
        outputs["issue_file"] = str(issue_copy)
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", required=True, choices=("implement", "review"))
    parser.add_argument("--workspace", default=os.environ.get("GITHUB_WORKSPACE"))
    parser.add_argument("--runtime-dir", required=True)
    parser.add_argument("--issue-file")
    arguments = parser.parse_args()
    try:
        if not arguments.workspace or not os.environ.get("RUNNER_TEMP") or not os.environ.get("GITHUB_RUN_ID"):
            raise RunnerSetupError("GITHUB_WORKSPACE, RUNNER_TEMP, and GITHUB_RUN_ID are required")
        outputs = prepare(
            arguments.mode, arguments.workspace, arguments.runtime_dir,
            os.environ["RUNNER_TEMP"], os.environ["GITHUB_RUN_ID"], arguments.issue_file,
        )
        text = "".join(f"{name}={value}\n" for name, value in outputs.items())
        if os.environ.get("GITHUB_OUTPUT"):
            output = physical_path(os.environ["GITHUB_OUTPUT"], directory=False)
            with output.open("a", encoding="utf-8") as stream:
                stream.write(text)
        print(text, end="")
    except (OSError, RunnerSetupError, subprocess.TimeoutExpired, UnicodeError, ValueError) as exc:
        print(f"Codex runner setup failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
