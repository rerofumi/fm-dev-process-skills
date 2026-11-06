#!/usr/bin/env python3
"""Optional content identity helper. Python 3.10+, standard library only."""

import argparse
import fnmatch
import hashlib
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import stat
import sys

VERSION = "1.0.0"
SCHEMA = "fm-artifact-identity-v1"
ALGORITHM = "sha256-canonical-file-list-v1"
HEX = re.compile(r"[0-9a-f]{64}\Z")


class IdentityError(Exception):
    pass


def canonical(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True,
                      separators=(",", ":")).encode("ascii")


def identity(files):
    # File contents are hashed individually: embedded path/NUL bytes cannot
    # shift boundaries between records, unlike path + NUL + raw content.
    payload = {"algorithm": ALGORITHM, "files": files}
    return "sha256:" + hashlib.sha256(canonical(payload)).hexdigest()


def tool_info():
    return {"name": "artifact_identity", "version": VERSION,
            "sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}


def pattern_parts(pattern):
    if (not isinstance(pattern, str) or not pattern or "\\" in pattern
            or PureWindowsPath(pattern).drive or pattern.startswith("/")):
        raise IdentityError("Patterns must be relative paths using '/' separators")
    parts = pattern.split("/")
    if any(p in ("", ".", "..") or ("**" in p and p != "**") for p in parts):
        raise IdentityError("Empty, dot, parent, or partial '**' segments are not supported")
    return parts


def states_after(parts, path_parts):
    def closure(states):
        result = set(states)
        for i in range(len(parts)):
            if i in result and parts[i] == "**":
                result.add(i + 1)
        return result

    states = closure({0})
    for segment in path_parts:
        states = closure({j for i in states if i < len(parts)
                          for j in ([i] if parts[i] == "**" else
                                    [i + 1] if fnmatch.fnmatchcase(segment, parts[i]) else [])})
    return states


def matches(parts, path_parts):
    return len(parts) in states_after(parts, path_parts)


def is_link(path):
    info = path.lstat()
    return (stat.S_ISLNK(info.st_mode)
            or bool(getattr(info, "st_file_attributes", 0)
                    & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)))


def select_files(root, patterns):
    compiled = [pattern_parts(p) for p in patterns]
    found = {}
    hits = [0] * len(patterns)

    def walk_error(error):
        raise error

    for directory, dirs, names in os.walk(root, topdown=True, followlinks=False,
                                          onerror=walk_error):
        parent = Path(directory)
        for name in list(dirs):
            path = parent / name
            relative = path.relative_to(root)
            # Prune branches which cannot contain selected files. Do not
            # silently omit a selected symlink/junction subtree.
            relevant = any(any(i < len(p) for i in states_after(p, relative.parts))
                           for p in compiled)
            if not relevant:
                dirs.remove(name)
            elif is_link(path):
                raise IdentityError(f"Selected directory is a link/reparse point: {relative}")
        for name in names:
            path = parent / name
            relative = path.relative_to(root)
            indices = [i for i, p in enumerate(compiled) if matches(p, relative.parts)]
            if not indices:
                continue
            if is_link(path) or not stat.S_ISREG(path.lstat().st_mode):
                raise IdentityError(f"Selected path is not a regular file: {relative}")
            found[relative.as_posix()] = path
            for i in indices:
                hits[i] += 1
    for pattern, count in zip(patterns, hits):
        if count == 0:
            raise IdentityError(f"Selection matched no files: {pattern}")
    return found


def signature(info):
    # Windows path stat and handle fstat can expose different ctime semantics.
    # Compare the stable shared fields rather than treating that as a mutation.
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)


def collect(root, patterns, expected_count=None):
    paths = select_files(root, patterns)
    if expected_count is not None and len(paths) != expected_count:
        raise IdentityError(f"Expected {expected_count} files, selected {len(paths)}")
    records, observed = [], {}
    for relative, path in sorted(paths.items()):
        before = path.stat()
        digest = hashlib.sha256()
        size = 0
        with path.open("rb") as stream:
            if signature(before) != signature(os.fstat(stream.fileno())):
                raise IdentityError(f"File changed before reading: {relative}")
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                size += len(chunk)
                digest.update(chunk)
            after = os.fstat(stream.fileno())
        if signature(before) != signature(after) or size != before.st_size:
            raise IdentityError(f"File changed while reading: {relative}")
        observed[relative] = signature(before)
        records.append({"path": relative, "size": size, "sha256": digest.hexdigest()})
    if set(select_files(root, patterns)) != set(paths):
        raise IdentityError("Selected file list changed while collecting")
    for relative, path in paths.items():
        if is_link(path) or signature(path.stat()) != observed[relative]:
            raise IdentityError(f"File changed during collection: {relative}")
    return records


def validate_snapshot(data):
    if not isinstance(data, dict) or data.get("schema") != SCHEMA:
        raise IdentityError("Unsupported snapshot schema")
    if data.get("algorithm") != ALGORITHM:
        raise IdentityError("Unsupported identity algorithm")
    patterns = data.get("include")
    if (not isinstance(patterns, list) or not patterns
            or any(not isinstance(p, str) for p in patterns)
            or patterns != sorted(set(patterns))):
        raise IdentityError("Invalid selection patterns")
    compiled = [pattern_parts(p) for p in patterns]
    files = data.get("files")
    if not isinstance(files, list) or not files:
        raise IdentityError("Snapshot has no file records")
    names = []
    for item in files:
        if not isinstance(item, dict) or set(item) != {"path", "size", "sha256"}:
            raise IdentityError("Invalid file record")
        name, size, digest = item["path"], item["size"], item["sha256"]
        if (not isinstance(name, str) or "\\" in name or not name
                or PureWindowsPath(name).drive or name.startswith("/")
                or any(p in ("", ".", "..") for p in name.split("/"))):
            raise IdentityError("Invalid file path in snapshot")
        if (type(size) is not int or size < 0 or not isinstance(digest, str)
                or not HEX.fullmatch(digest)):
            raise IdentityError("Invalid file size/hash in snapshot")
        if not any(matches(p, PurePosixPath(name).parts) for p in compiled):
            raise IdentityError("File record falls outside declared selection")
        names.append(name)
    if names != sorted(set(names)):
        raise IdentityError("File paths must be sorted and unique")
    if (type(data.get("file_count")) is not int or data["file_count"] != len(files)
            or type(data.get("total_bytes")) is not int
            or data["total_bytes"] != sum(f["size"] for f in files)
            or data.get("identity") != identity(files)):
        raise IdentityError("Snapshot count/size/identity is inconsistent")
    return patterns, files


def read_snapshot(path):
    def unique_keys(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise IdentityError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_keys)


def write_snapshot(path, data):
    raw = json.dumps(data, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    # Exclusive creation preserves every existing baseline, including on error.
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(raw)
    if read_snapshot(path) != data:
        raise IdentityError("Snapshot readback did not match; do not use this file")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=VERSION)
    commands = parser.add_subparsers(dest="command", required=True)
    snapshot = commands.add_parser("snapshot", help="Collect content IDs; optionally save a new JSON file")
    snapshot.add_argument("--root", required=True, type=Path)
    snapshot.add_argument("--include", required=True, action="append", help="Relative glob; repeat for multiple sets")
    snapshot.add_argument("--expect-count", type=int)
    snapshot.add_argument("--output", type=Path, help="New file only; existing files are never overwritten")
    verify = commands.add_parser("verify", help="Read-only comparison against a recorded selection")
    verify.add_argument("--root", required=True, type=Path)
    verify.add_argument("--snapshot", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve(strict=True)
        if not root.is_dir():
            raise IdentityError("Root must be a directory")
        if args.command == "snapshot":
            patterns = sorted(set(args.include))
            for pattern in patterns:
                pattern_parts(pattern)
            if args.expect_count is not None and args.expect_count <= 0:
                raise IdentityError("Expected count must be positive")
            if args.output:
                output = args.output.resolve()
                if output.exists():
                    raise IdentityError("Output already exists; choose a new snapshot path")
                if output.is_relative_to(root) and any(
                        matches(pattern_parts(p), output.relative_to(root).parts) for p in patterns):
                    raise IdentityError("Output must be outside the selected file set")
            files = collect(root, patterns, args.expect_count)
            result = {"schema": SCHEMA, "algorithm": ALGORITHM,
                      "tool": tool_info(),
                      "include": patterns, "file_count": len(files),
                      "total_bytes": sum(f["size"] for f in files),
                      "files": files, "identity": identity(files)}
            if args.output:
                write_snapshot(args.output, result)
            code = 0
        else:
            baseline = read_snapshot(args.snapshot)
            patterns, old_files = validate_snapshot(baseline)
            files = collect(root, patterns)
            old = {f["path"]: f for f in old_files}
            new = {f["path"]: f for f in files}
            result = {"status": "match" if files == old_files else "mismatch",
                      "tool": tool_info(),
                      "expected_identity": baseline["identity"], "actual_identity": identity(files),
                      "file_count": len(files), "include": patterns,
                      "added": sorted(new.keys() - old.keys()),
                      "removed": sorted(old.keys() - new.keys()),
                      "modified": sorted(p for p in old.keys() & new.keys() if old[p] != new[p])}
            code = 0 if files == old_files else 1
        print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
        return code
    except (IdentityError, OSError, ValueError, RuntimeError) as error:
        print(json.dumps({"status": "error", "message": str(error)}, ensure_ascii=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
