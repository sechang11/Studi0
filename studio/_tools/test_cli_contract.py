#!/usr/bin/env python3
"""studio/_tools/test_cli_contract.py - no NEW tool may run its whole job on --help.

    python3 studio/_tools/test_cli_contract.py            exit 1 if a new offender appeared
    python3 studio/_tools/test_cli_contract.py --list     show the grandfathered ones
    python3 studio/_tools/test_cli_contract.py --update   accept the current set as the baseline

THE HAZARD, WHICH IS ALREADY DOCUMENTED AND ALREADY BIT. Roughly twenty tools here have no
argparse and do their work at module level, so passing ANY argument - including --help -
runs the entire job. Several write files while doing it. That is why /tools has to be a
hand-curated allowlist of fourteen rather than a generic runner: the folder cannot be
safely enumerated, let alone safely invoked.

audit.py reports this. Reporting is not enforcing: the count has only ever gone up, and I
added one to it myself this session while fixing other things.

WHY A FROZEN BASELINE RATHER THAN A CLEAN SWEEP. Fixing all seventeen at once means
seventeen behaviour changes in one commit, in tools whose whole value is that their output
is comparable to last time. REFACTOR.md is explicit that refactor and behaviour change must
not share a commit. So the existing offenders are named in a baseline file, and the test
fails only on a NEW one. The list can shrink and never grow, which is the property that
actually matters: the pile stops getting bigger today, and gets smaller as tools are
touched for other reasons.

WHAT COUNTS AS COMPLIANT. Either the module parses arguments (argparse anywhere), or it
does nothing at import beyond definitions - no calls at module level other than the usual
path and constant setup. A __main__ guard alone is not enough if the guard runs an
unguarded job on arbitrary argv, but it is enough to stop an IMPORT from doing work, which
is the part that makes a folder unsafe to enumerate.
"""
import argparse, ast, json, os, sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
BASELINE = os.path.join(TOOLS, "_cli_contract_baseline.json")

# Module-level calls that are setup, not work. Anything else executing at import is work.
ALLOWED_CALLS = {
    "dirname", "abspath", "join", "insert", "append", "getenv", "setdefault",
    "expanduser", "basename", "normpath", "compile", "getcwd", "environ",
    "Counter", "defaultdict", "namedtuple", "dataclass", "TypeVar", "Path",
}


def module_level_work(tree):
    """Calls that run at import, ignoring the ones that are obviously configuration."""
    out = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef,
                             ast.Import, ast.ImportFrom, ast.Assign, ast.AnnAssign,
                             ast.Expr, ast.If, ast.Try)):
            # An Expr at module level is usually a docstring; a bare call is not.
            if isinstance(node, ast.Expr) and not isinstance(node.value, ast.Call):
                continue
            if isinstance(node, ast.If):
                continue          # __main__ guards and feature checks
        for sub in ast.walk(node):
            if not isinstance(sub, ast.Call):
                continue
            f = sub.func
            name = getattr(f, "attr", None) or getattr(f, "id", None)
            if name in ALLOWED_CALLS:
                continue
            # Only count calls that are genuinely at module level, not inside a def.
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            out.append(name or "?")
    return out


def offenders():
    bad = {}
    for fn in sorted(os.listdir(TOOLS)):
        if not fn.endswith(".py") or fn.startswith("_"):
            continue
        p = os.path.join(TOOLS, fn)
        try:
            src = open(p, encoding="utf-8", errors="replace").read()
            tree = ast.parse(src)
        except Exception:
            continue
        if "argparse" in src:
            continue
        if fn.endswith("_routes.py"):
            continue          # imported by serve.py, never run from a shell
        work = module_level_work(tree)
        if work:
            bad[fn] = sorted(set(work))[:6]
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--update", action="store_true")
    a = ap.parse_args()

    now = offenders()
    base = {}
    if os.path.isfile(BASELINE):
        try:
            base = json.load(open(BASELINE, encoding="utf-8"))
        except Exception:
            base = {}

    if a.update:
        json.dump({"grandfathered": sorted(now)}, open(BASELINE, "w", encoding="utf-8"),
                  indent=1)
        print("  baseline set to %d tool(s)" % len(now))
        return 0

    known = set(base.get("grandfathered", []))
    if a.list:
        for fn in sorted(now):
            print("  %-38s %s" % (fn, ", ".join(now[fn])))
        print("\n  %d tool(s) without a CLI contract, %d grandfathered"
              % (len(now), len(known)))
        return 0

    new = sorted(set(now) - known)
    gone = sorted(known - set(now))
    for fn in gone:
        print("  FIXED: %s no longer runs its job at import" % fn)
    if gone:
        print("  -> run --update to shrink the baseline; it may never grow.")
    if new:
        print("\n  %d NEW tool(s) with no CLI contract:" % len(new))
        for fn in new:
            print("    %-36s runs at import: %s" % (fn, ", ".join(now[fn])))
        print("\n  A tool with no argparse runs its ENTIRE job on any argument, including")
        print("  --help, and several here write files while doing it. Give it argparse, or")
        print("  move its work inside a main() behind a __main__ guard.")
        return 1
    print("  no new CLI-contract offenders (%d grandfathered)" % len(known))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
