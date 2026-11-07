#!/usr/bin/env python3
"""check_mirror.py — source docs and packaged skills drift check.

`docs/develop_document/` is the source of truth; `skills/` holds the packaged
copies. The pairs must stay body-identical apart from YAML frontmatter and
cross-link paths. This tool normalizes those known differences and fails
(non-zero exit) on real drift, and reports per-file line counts (optionally
against a baseline for before/after revision deltas).

Standard library only.

Usage:
  python scripts/check_mirror.py                # check all pairs, print report
  python scripts/check_mirror.py --verbose      # also show diff lines for drift
  python scripts/check_mirror.py --save-baseline FILE
  python scripts/check_mirror.py --baseline FILE
Exit codes: 0 = clean, 1 = drift or baseline delta, 2 = usage/IO error.
"""

import argparse
import difflib
import json
import re
import sys
from pathlib import Path

ROLES = [
    "acceptance", "architect", "cheatsheet", "develop", "implement", "plan",
    "process", "release", "requirement", "reviewer", "taskplanner", "tester",
]

PAIRS = [
    ("docs/develop_document/00_common.md",
     "skills/fm-dev-process/references/workflow-contract.md"),
    ("docs/develop_document/00_documents.md",
     "skills/fm-dev-process/references/document-roles.md"),
] + [
    (f"docs/develop_document/fm-dev-{r}.md", f"skills/fm-dev-{r}/SKILL.md")
    for r in ROLES
]

# Unpaired files still tracked for line-count/baseline reports.
SOLO_FILES = [
    "docs/develop_document/UPDATE.md",
    "skills/fm-dev-process/references/cheatsheet-rules.md",
]

LINK_RE = re.compile(r"\]\(([^)]+)\)")


def canonical_target(target: str) -> str:
    """Map a link target to a path-independent canonical token."""
    t = target.strip().strip('"').strip("'")
    t = t.split("#", 1)[0]          # drop anchor
    t = t.split(" ", 1)[0]          # drop optional markdown link title
    t = t.replace("\\", "/")
    if not t:
        return t
    base = t.split("/")[-1].lower()
    if base in ("00_common.md", "workflow-contract.md"):
        return "@contract"
    if base in ("00_documents.md", "document-roles.md"):
        return "@documents"
    m = re.fullmatch(r"fm-dev-([a-z]+)\.md", base)
    if m:
        return f"@role:{m.group(1)}"
    parts = t.split("/")
    if len(parts) >= 2 and parts[-1].lower() == "skill.md":
        m2 = re.fullmatch(r"fm-dev-([a-z]+)", parts[-2].lower())
        if m2:
            return f"@role:{m2.group(1)}"
    return base


def normalize(text: str) -> list:
    """Strip frontmatter, normalize newlines/line ends and link targets."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    if lines and lines[0].strip() == "---":
        for i in range(1, min(len(lines), 30)):
            if lines[i].strip() == "---":
                lines = lines[i + 1:]
                if lines and lines[0].strip() == "":
                    lines = lines[1:]
                break
    out = []
    for line in lines:
        line = line.rstrip()
        line = LINK_RE.sub(lambda m: "](%s)" % canonical_target(m.group(1)), line)
        out.append(line)
    return out


def count_lines(path: Path) -> int:
    """Line count for budget reporting (matches `wc -l` for newline-terminated files)."""
    return len(path.read_text(encoding="utf-8-sig").splitlines())


def check_pair(root: Path, src_rel: str, mir_rel: str, verbose: bool):
    src, mir = root / src_rel, root / mir_rel
    for p in (src, mir):
        if not p.is_file():
            print(f"ERROR missing file: {p}")
            return None
    a, b = normalize(src.read_text(encoding="utf-8-sig")), \
           normalize(mir.read_text(encoding="utf-8-sig"))
    src_lines = count_lines(src)
    mir_lines = count_lines(mir)
    if a == b:
        return {"ok": True, "src": src_rel, "mirror": mir_rel,
                "src_lines": src_lines, "mirror_lines": mir_lines}
    print(f"DRIFT  {src_rel}  <->  {mir_rel}")
    if verbose:
        for d in difflib.unified_diff(a, b, fromfile=src_rel, tofile=mir_rel,
                                     lineterm="", n=1):
            print("   " + d)
    else:
        diff = [d for d in difflib.unified_diff(a, b, lineterm="", n=0)
                if d[:1] in "+-" and d[:3] not in ("+++", "---")]
        for d in diff[:12]:
            print("   " + d[:160])
        if len(diff) > 12:
            print(f"   ... {len(diff) - 12} more diff lines (--verbose to show)")
    return {"ok": False, "src": src_rel, "mirror": mir_rel,
            "src_lines": src_lines, "mirror_lines": mir_lines}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", type=Path,
                    default=Path(__file__).resolve().parent.parent,
                    help="repository root (default: parent of scripts/)")
    ap.add_argument("--verbose", action="store_true",
                    help="show full diff for drifting pairs")
    ap.add_argument("--save-baseline", type=Path, metavar="FILE",
                    help="write current per-file line counts to FILE and exit")
    ap.add_argument("--baseline", type=Path, metavar="FILE",
                    help="compare line counts against FILE and report deltas")
    ap.add_argument("--max-total", type=int, metavar="N",
                    help="with --baseline: exit 0 while total delta stays <= N")
    args = ap.parse_args()
    root = args.root.resolve()

    results = []
    for src_rel, mir_rel in PAIRS:
        r = check_pair(root, src_rel, mir_rel, args.verbose)
        if r is None:
            return 2
        results.append(r)

    counts = {}
    for r in results:
        counts[r["src"]] = r["src_lines"]
        counts[r["mirror"]] = r["mirror_lines"]
    for rel in SOLO_FILES:
        p = root / rel
        if not p.is_file():
            print(f"ERROR missing file: {p}")
            return 2
        counts[rel] = count_lines(p)

    ok_n = sum(1 for r in results if r["ok"])
    print(f"\nmirror check: {ok_n}/{len(results)} pairs clean")
    print("line counts:")
    for r in results:
        flag = "ok" if r["ok"] else "DRIFT"
        print(f"  [{flag:>5}] {r['src']:<48} {r['src_lines']:>4}  <->  "
              f"{r['mirror']:<56} {r['mirror_lines']:>4}")
    print(f"  total lines (pairs): source={sum(r['src_lines'] for r in results)} "
          f"mirror={sum(r['mirror_lines'] for r in results)}")
    for rel in SOLO_FILES:
        print(f"  [ solo] {rel:<48} {counts[rel]:>4}")

    if args.save_baseline:
        args.save_baseline.write_text(
            json.dumps(counts, indent=2, sort_keys=True) + "\n",
            encoding="utf-8")
        print(f"\nbaseline saved: {args.save_baseline} ({len(counts)} files)")
        return 0 if ok_n == len(results) else 1

    if args.baseline:
        if not args.baseline.is_file():
            print(f"ERROR baseline not found: {args.baseline}")
            return 2
        base = json.loads(args.baseline.read_text(encoding="utf-8"))
        print("\nbaseline deltas:")
        total = 0
        for path in sorted(set(base) | set(counts)):
            before, after = base.get(path), counts.get(path)
            if before == after:
                continue
            total += (after or 0) - (before or 0)
            where = path if before is not None and after is not None else \
                path + (" (new)" if before is None else " (removed)")
            print(f"  {where:<60} {before!s:>4} -> {after!s:>4} "
                  f"({(after or 0) - (before or 0):+d})")
        if total == 0:
            print("  (no line-count changes)")
        else:
            print(f"  total delta: {total:+d}")
        if args.max_total is not None:
            within = total <= args.max_total
            print(f"  budget check: total {total:+d} vs limit +{args.max_total} -> "
                  f"{'WITHIN' if within else 'OVER'}")
            return 0 if ok_n == len(results) and within else 1
        return 0 if ok_n == len(results) and total == 0 else 1

    return 0 if ok_n == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
