#!/usr/bin/env python3
"""Extract every fenced code block from docs/ and test it.

Every fence in docs/**/*.md must be preceded by a marker comment (the nearest
non-blank line above it, same indentation) that says what to do with it:

    <!-- snippet: run -->                 execute it (keyless; must succeed)
    <!-- snippet: check -->               key-needing / side-effecting: syntax and
                                          import/flag check only, never executed
    <!-- snippet: skip -->                illustrative fragment: not tested

Options follow the mode as key=value (or bare flags):

    file=NAME       write the block to NAME in the page's work dir (all modes), so
                    later blocks on the same page can use it (my_agent.py, ...)
    needs=A,B       copy these fixtures from tests/snippets/fixtures/ into the work
                    dir before the block runs (e.g. needs=my_agent.py)
    timeout=SEC     hard time limit for a run (default 180)
    exit=0,2        accepted exit codes (default 0)
    each            bash: run every command line as its own process
    server[=SEC]    like `each`, but a line that is still running after SEC seconds
                    (default 12) counts as a healthy server / interactive session
                    and is killed. stdin stays open and silent, as in a terminal.
    no-errexit      bash: don't `set -e` (for blocks that inspect `$?` themselves)

What each mode does, by language:

    python  run: execute as a script.  check: compile + execute its imports only.
    bash    run: execute (set -eo pipefail unless no-errexit).
            check: `bash -n`, and every langstage entry point it calls must exist
            and advertise every --flag / subcommand the block uses (`--help`).
    toml    check: parse.   json   check: parse (whole block or one doc per line).
    other   only skip is allowed.

Inside tabs / admonitions (indented fences), leave a blank line between the
marker and the fence, or Markdown wraps the comment and the code in a <p>.

Blocks on one page share a fresh temp work dir and run in document order; HOME
and the LangStage/Hermes config dirs point into it and provider API keys are
removed from the environment, so "keyless" is actually verified.

Usage:
    python scripts/snippets.py lint                    # every fence is marked?
    python scripts/snippets.py list                    # counts per mode
    python scripts/snippets.py run --python .venv-snippets/bin/python \
        [--page stages/cli.md] [--report report.md] [--json results.json]
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
FIXTURES = ROOT / "tests" / "snippets" / "fixtures"

MARKER_RE = re.compile(r"^\s*<!--\s*snippet:\s*(\w+)\s*(.*?)\s*-->\s*$")
FENCE_RE = re.compile(r"^(\s*)(`{3,}|~{3,})\s*([\w+-]*)(.*)$")
MODES = {"run", "check", "skip"}
KNOWN_OPTS = {"file", "needs", "timeout", "exit", "each", "server", "no-errexit"}
LANG_ALIASES = {"sh": "bash", "shell": "bash", "console": "bash", "py": "python", "python3": "python"}
# Console scripts shipped by the six packages. `check` verifies flags against these.
ENTRYPOINTS = {
    "langstage", "langstage-cli", "langstage-jupyter", "langstage-vscode-sidecar",
    "langstage-hermes", "langstage-agui",
}
SCRUBBED_ENV = (
    "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OPENROUTER_API_KEY", "GOOGLE_API_KEY",
    "GEMINI_API_KEY", "LANGSMITH_API_KEY", "LANGCHAIN_API_KEY", "LANGSMITH_TRACING",
)
DEFAULT_TIMEOUT = 180
DEFAULT_SERVER_WAIT = 12
IS_WINDOWS = os.name == "nt"


@dataclass
class Block:
    page: str          # path relative to docs/
    line: int          # 1-based line of the opening fence
    lang: str
    code: str
    mode: str | None
    opts: dict = field(default_factory=dict)
    marker_error: str | None = None

    @property
    def where(self) -> str:
        return f"docs/{self.page}:{self.line}"


@dataclass
class Result:
    block: Block
    status: str        # pass | fail | skip
    detail: str = ""
    seconds: float = 0.0


# ---------------------------------------------------------------- extraction

def parse_opts(text: str) -> dict:
    opts: dict = {}
    for tok in shlex.split(text):
        key, _, val = tok.partition("=")
        opts[key] = val if _ else True
    return opts


def extract(path: Path) -> list[Block]:
    rel = path.relative_to(DOCS).as_posix()
    lines = path.read_text(encoding="utf-8").splitlines()
    blocks: list[Block] = []
    i = 0
    while i < len(lines):
        m = FENCE_RE.match(lines[i])
        if not m:
            i += 1
            continue
        indent, fence, lang = m.group(1), m.group(2), m.group(3).lower()
        j = i + 1
        body: list[str] = []
        while j < len(lines):
            s = lines[j]
            if s.strip().startswith(fence) and s.strip().strip(fence[0]) == "":
                break
            body.append(s[len(indent):] if s.startswith(indent) else s.lstrip())
            j += 1
        mode, opts, err = None, {}, None
        k = i - 1
        while k >= 0 and not lines[k].strip():
            k -= 1          # blank lines between marker and fence are allowed
        mm = MARKER_RE.match(lines[k]) if k >= 0 else None
        if mm:
            mode = mm.group(1)
            try:
                opts = parse_opts(mm.group(2))
            except ValueError as exc:
                err = f"unparsable marker options: {exc}"
            if mode not in MODES:
                err = f"unknown snippet mode {mode!r} (use run, check or skip)"
            unknown = set(opts) - KNOWN_OPTS
            if unknown and not err:
                err = f"unknown marker option(s): {', '.join(sorted(unknown))}"
        else:
            err = "no <!-- snippet: run|check|skip --> marker on the line above this fence"
        lang = LANG_ALIASES.get(lang, lang)
        if not err and mode != "skip" and lang not in {"python", "bash", "toml", "json"}:
            err = f"mode {mode!r} is not supported for {lang or 'unlabelled'} fences (use skip)"
        if not err and mode == "run" and lang in {"toml", "json"}:
            err = f"{lang} blocks can't run; use check (parse) or skip"
        blocks.append(Block(rel, i + 1, lang, "\n".join(body) + "\n", mode, opts, err))
        i = j + 1
    return blocks


def all_blocks(page: str | None = None) -> list[Block]:
    out: list[Block] = []
    for p in sorted(DOCS.rglob("*.md")):
        rel = p.relative_to(DOCS).as_posix()
        if page and rel != page:
            continue
        out.extend(extract(p))
    return out


def orphan_markers() -> list[str]:
    bad = []
    for p in sorted(DOCS.rglob("*.md")):
        lines = p.read_text(encoding="utf-8").splitlines()
        for n, s in enumerate(lines):
            if not MARKER_RE.match(s):
                continue
            k = n + 1
            while k < len(lines) and not lines[k].strip():
                k += 1
            if not (k < len(lines) and FENCE_RE.match(lines[k])):
                bad.append(f"docs/{p.relative_to(DOCS).as_posix()}:{n + 1}: marker is not directly above a fence")
    return bad


# ---------------------------------------------------------------- process helpers

def kill_tree(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    if IS_WINDOWS:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                proc.wait(5)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    try:
        proc.wait(10)
    except subprocess.TimeoutExpired:
        pass


def spawn(argv: list[str], cwd: Path, env: dict, log: Path, hold_stdin: bool) -> subprocess.Popen:
    fh = open(log, "wb")
    kw: dict = {}
    if IS_WINDOWS:
        kw["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kw["start_new_session"] = True
    # A server / interactive session gets an open, silent stdin (it waits, as it
    # would in a terminal); everything else gets EOF.
    stdin = subprocess.PIPE if hold_stdin else subprocess.DEVNULL
    return subprocess.Popen(argv, cwd=cwd, env=env, stdin=stdin,
                            stdout=fh, stderr=subprocess.STDOUT, **kw)


def tail(log: Path, n: int = 40) -> str:
    try:
        text = log.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return "\n".join(text.splitlines()[-n:])


def run_proc(argv: list[str], cwd: Path, env: dict, timeout: float,
             server_wait: float | None = None) -> tuple[str, int | None, str]:
    """Return (state, exit_code, output_tail). state: exited | timeout | alive."""
    fd, logname = tempfile.mkstemp(prefix="snippet-", suffix=".log", dir=cwd)
    os.close(fd)
    log = Path(logname)
    proc = spawn(argv, cwd, env, log, hold_stdin=server_wait is not None)
    limit = server_wait if server_wait is not None else timeout
    try:
        proc.wait(limit)
        state = "exited"
    except subprocess.TimeoutExpired:
        state = "alive" if server_wait is not None else "timeout"
        kill_tree(proc)
    out = tail(log)
    try:
        log.unlink()
    except OSError:
        pass
    return state, proc.returncode, out


# ---------------------------------------------------------------- bash helpers

def logical_lines(code: str) -> list[str]:
    out, buf = [], ""
    for raw in code.splitlines():
        s = raw.rstrip()
        if s.endswith("\\"):
            buf += s[:-1] + " "
            continue
        s = buf + s
        buf = ""
        if s.strip() and not s.strip().startswith("#"):
            out.append(s.strip())
    return out


def command_segments(line: str) -> list[list[str]]:
    lex = shlex.shlex(line, posix=True, punctuation_chars=";&|()<>")
    lex.whitespace_split = True
    lex.commenters = "#"
    try:
        toks = list(lex)
    except ValueError:
        return []
    segs, cur = [], []
    for t in toks:
        if t and set(t) <= set(";&|()<>"):
            if cur:
                segs.append(cur)
            cur = []
        else:
            cur.append(t)
    if cur:
        segs.append(cur)
    cleaned = []
    for seg in segs:
        while seg and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", seg[0]):
            seg = seg[1:]           # VAR=value cmd
        if seg and seg[0] in {"export", "echo", "cat", "cd", "set"}:
            continue
        if seg:
            cleaned.append(seg)
    return cleaned


_help_cache: dict[tuple, str] = {}


def help_text(bindir: Path, argv: list[str], env: dict) -> str | None:
    key = tuple(argv)
    if key not in _help_cache:
        exe = shutil.which(argv[0], path=str(bindir))
        if not exe:
            _help_cache[key] = None
        else:
            try:
                cp = subprocess.run([exe, *argv[1:], "--help"], capture_output=True, text=True,
                                    env=env, timeout=60, stdin=subprocess.DEVNULL,
                                    encoding="utf-8", errors="replace")
                _help_cache[key] = cp.stdout + cp.stderr if cp.returncode == 0 else None
            except subprocess.TimeoutExpired:
                _help_cache[key] = None
    return _help_cache[key]


def check_entrypoint_flags(seg: list[str], bindir: Path, env: dict) -> list[str]:
    cmd = seg[0]
    if cmd not in ENTRYPOINTS:
        return []
    base = help_text(bindir, [cmd], env)
    if base is None:
        return [f"`{cmd}` is not installed (or `{cmd} --help` fails)"]
    texts = [base]
    path = [cmd]
    # Walk subcommands: a leading bare word that a --help lists as a command.
    for tok in seg[1:3]:
        if tok.startswith("-") or not re.fullmatch(r"[a-z][a-z0-9-]*", tok):
            break
        if not re.search(rf"(?m)^\s*\{{?[\w,-]*\b{re.escape(tok)}\b", texts[-1]):
            break
        sub = help_text(bindir, [*path, tok], env)
        if sub is None:
            break
        path.append(tok)
        texts.append(sub)
    corpus = "\n".join(texts)
    problems = []
    for tok in seg[1:]:
        if tok == "--" or not tok.startswith("-") or re.fullmatch(r"-\d+", tok):
            continue
        flag = tok.split("=", 1)[0]
        if not re.search(rf"(?<![\w-]){re.escape(flag)}(?![\w-])", corpus):
            problems.append(f"`{' '.join(path)}` does not advertise `{flag}` in --help")
    return problems


# ---------------------------------------------------------------- runners

class Runner:
    def __init__(self, python: Path, keep: bool = False):
        self.python = python.resolve() if python.exists() else python
        self.bindir = self.python.parent
        self.keep = keep
        self.bash = shutil.which("bash") or "bash"

    def env_for(self, work: Path) -> dict:
        env = {k: v for k, v in os.environ.items() if k not in SCRUBBED_ENV}
        home = work / ".home"
        home.mkdir(exist_ok=True)
        env.update({
            "PATH": str(self.bindir) + os.pathsep + env.get("PATH", ""),
            "VIRTUAL_ENV": str(self.bindir.parent),
            "HOME": str(home), "USERPROFILE": str(home),
            "LANGSTAGE_CONFIG_HOME": str(home / ".langstage"),
            "HERMES_HOME": str(home / ".hermes"),
            "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1",
            "PIP_DISABLE_PIP_VERSION_CHECK": "1",
            "NO_COLOR": "1", "BROWSER": "true",
        })
        env.pop("PYTHONPATH", None)
        return env

    def run_page(self, blocks: list[Block]) -> list[Result]:
        work = Path(tempfile.mkdtemp(prefix="docs-snippets-"))
        env = self.env_for(work)
        results = []
        try:
            for i, b in enumerate(blocks):
                t0 = time.monotonic()
                try:
                    status, detail = self.run_block(b, i, work, env)
                except Exception as exc:  # a harness bug must not hide other results
                    status, detail = "fail", f"harness error: {exc!r}"
                results.append(Result(b, status, detail, time.monotonic() - t0))
                mark = {"pass": "ok  ", "fail": "FAIL", "skip": "skip"}[status]
                print(f"  {mark} {b.where:<52} {b.mode:<5} {b.lang:<6} "
                      f"{results[-1].seconds:5.1f}s", flush=True)
                if status == "fail":
                    print("       " + detail.replace("\n", "\n       ")[:4000], flush=True)
        finally:
            if not self.keep:
                shutil.rmtree(work, ignore_errors=True)
        return results

    def run_block(self, b: Block, idx: int, work: Path, env: dict) -> tuple[str, str]:
        for name in str(b.opts.get("needs", "")).split(","):
            if name:
                src = FIXTURES / name
                if not src.exists():
                    return "fail", f"fixture {name!r} not found in tests/snippets/fixtures/"
                shutil.copy(src, work / name)
        target = None
        if b.opts.get("file"):
            target = work / str(b.opts["file"])
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(b.code, encoding="utf-8")
        if b.mode == "skip":
            return "skip", ""
        timeout = float(b.opts.get("timeout", DEFAULT_TIMEOUT))
        codes = {int(c) for c in str(b.opts.get("exit", "0")).split(",")}
        if b.lang == "toml":
            try:
                tomllib.loads(b.code)
            except tomllib.TOMLDecodeError as exc:
                return "fail", f"TOML does not parse: {exc}"
            return "pass", ""
        if b.lang == "json":
            try:
                json.loads(b.code)
            except json.JSONDecodeError:
                for n, line in enumerate(b.code.splitlines(), 1):
                    if line.strip():
                        try:
                            json.loads(line)
                        except json.JSONDecodeError as exc:
                            return "fail", f"JSON line {n} does not parse: {exc}"
            return "pass", ""
        if b.lang == "python":
            return self.python_block(b, idx, work, env, target, timeout, codes)
        return self.bash_block(b, idx, work, env, timeout, codes)

    def python_block(self, b, idx, work, env, target, timeout, codes):
        try:
            tree = ast.parse(b.code, filename=b.where)
        except SyntaxError as exc:
            return "fail", f"SyntaxError: {exc}"
        if b.mode == "check":
            imports = [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
            if not imports:
                return "pass", "(compiled; no imports)"
            src = "\n".join(ast.unparse(n) for n in imports) + "\n"
            script = work / f"_snippet_{idx}_imports.py"
            script.write_text(src, encoding="utf-8")
            state, rc, out = run_proc([str(self.python), script.name], work, env, timeout)
            if state != "exited" or rc != 0:
                return "fail", f"imports failed (exit {rc}, {state}):\n{src}\n{out}"
            return "pass", ""
        script = target or (work / f"_snippet_{idx}.py")
        if target is None:
            script.write_text(b.code, encoding="utf-8")
        server = b.opts.get("server")
        wait = None
        if server:
            wait = float(DEFAULT_SERVER_WAIT if server is True else server)
        state, rc, out = run_proc([str(self.python), script.name], work, env, timeout, wait)
        if state == "alive":
            return "pass", ""
        if state == "timeout":
            return "fail", f"timed out after {timeout:.0f}s:\n{out}"
        if rc not in codes:
            return "fail", f"exit {rc} (expected {sorted(codes)}):\n{out}"
        return "pass", ""

    def bash_block(self, b, idx, work, env, timeout, codes):
        code = b.code
        if b.mode == "check":
            # `<name>`-style placeholders are prose, not redirections.
            code = re.sub(r"<([A-Za-z][\w-]*)>", r"PLACEHOLDER_\1", code)
        script = work / f"_snippet_{idx}.sh"
        script.write_text(code, encoding="utf-8", newline="\n")
        cp = subprocess.run([self.bash, "-n", script.name], cwd=work, capture_output=True, text=True)
        if cp.returncode != 0:
            return "fail", f"bash -n: {cp.stderr.strip()}"
        if b.mode == "check":
            problems = []
            for line in logical_lines(code):
                for seg in command_segments(line):
                    problems += check_entrypoint_flags(seg, self.bindir, env)
            return ("fail", "\n".join(dict.fromkeys(problems))) if problems else ("pass", "")
        server = b.opts.get("server")
        if server or b.opts.get("each"):
            wait = None
            if server:
                wait = float(DEFAULT_SERVER_WAIT if server is True else server)
            for line in logical_lines(b.code):
                state, rc, out = run_proc([self.bash, "-o", "pipefail", "-c", line],
                                          work, env, timeout, wait)
                if state == "timeout":
                    return "fail", f"`{line}` timed out after {timeout:.0f}s:\n{out}"
                if state == "exited" and rc not in codes:
                    return "fail", f"`{line}` exited {rc} (expected {sorted(codes)}):\n{out}"
            return "pass", ""
        flags = ["-o", "pipefail"] + ([] if b.opts.get("no-errexit") else ["-e"])
        state, rc, out = run_proc([self.bash, *flags, script.name], work, env, timeout)
        if state == "timeout":
            return "fail", f"timed out after {timeout:.0f}s:\n{out}"
        if rc not in codes:
            return "fail", f"exit {rc} (expected {sorted(codes)}):\n{out}"
        return "pass", ""


# ---------------------------------------------------------------- reporting

def counts(blocks: list[Block]) -> dict:
    c = {"run": 0, "check": 0, "skip": 0}
    for b in blocks:
        if b.mode in c:
            c[b.mode] += 1
    return c


def write_report(results: list[Result], path: Path) -> None:
    fails = [r for r in results if r.status == "fail"]
    c = counts([r.block for r in results])
    lines = [
        f"**Snippets:** {len(results)} blocks: {c['run']} run, {c['check']} check, {c['skip']} skip. "
        f"**{len(fails)} failing.**",
        "",
    ]
    for r in fails:
        lines += [f"<details><summary><code>{r.block.where}</code> ({r.block.mode}, {r.block.lang})</summary>",
                  "", "```text", r.detail.strip()[-3000:], "```", "", "</details>", ""]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("lint", help="fail if any fence lacks a valid marker")
    sub.add_parser("list", help="print every block with its mode")
    r = sub.add_parser("run", help="execute / check the snippets")
    r.add_argument("--python", required=True, type=Path,
                   help="python of the venv the packages are installed in")
    r.add_argument("--page", help="only this page (path relative to docs/)")
    r.add_argument("--report", type=Path, help="write a Markdown summary here")
    r.add_argument("--json", type=Path, help="write machine-readable results here")
    r.add_argument("--keep", action="store_true", help="keep the temp work dirs")
    args = ap.parse_args()

    blocks = all_blocks(getattr(args, "page", None))
    errors = [f"{b.where}: {b.marker_error}" for b in blocks if b.marker_error] + orphan_markers()

    if args.cmd == "list":
        for b in blocks:
            print(f"{b.where:<52} {b.mode or '-':<5} {b.lang:<6} {' '.join(f'{k}={v}' for k, v in b.opts.items())}")
    if args.cmd in {"lint", "list"} or errors:
        c = counts(blocks)
        print(f"{len(blocks)} blocks: {c['run']} run, {c['check']} check, {c['skip']} skip")
        for e in errors:
            print(f"error: {e}", file=sys.stderr)
        return 1 if errors else 0

    by_page: dict[str, list[Block]] = {}
    for b in blocks:
        by_page.setdefault(b.page, []).append(b)
    runner = Runner(args.python, keep=args.keep)
    results: list[Result] = []
    for page, pblocks in by_page.items():
        print(f"docs/{page}", flush=True)
        results += runner.run_page(pblocks)
    fails = [x for x in results if x.status == "fail"]
    c = counts(blocks)
    print(f"\n{len(results)} blocks: {c['run']} run, {c['check']} check, {c['skip']} skip; "
          f"{len(fails)} failing")
    if args.report:
        write_report(results, args.report)
    if args.json:
        args.json.write_text(json.dumps({
            "counts": c, "failing": len(fails),
            "failures": [{"where": x.block.where, "mode": x.block.mode, "lang": x.block.lang,
                          "detail": x.detail} for x in fails],
        }, indent=2), encoding="utf-8")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
