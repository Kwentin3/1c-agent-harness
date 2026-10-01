#!/usr/bin/env python3
"""Small reproducible front doors for the Issue #51 comparison."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
import re
import subprocess
import time
import xml.etree.ElementTree as ET


def emit(event: dict) -> None:
    event = {"timeNs": time.time_ns(), **event}
    log = os.environ.get("ISSUE51_LOG")
    if log:
        with Path(log).open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    print(json.dumps(event, ensure_ascii=False, sort_keys=True))


def build_catalog(snapshot: Path, output: Path) -> None:
    started = time.perf_counter_ns()
    metadata: list[str] = []
    root = ET.parse(snapshot / "ConfigDumpInfo.xml").getroot()
    versions = next(child for child in root if child.tag.endswith("ConfigVersions"))
    for node in versions:
        name = node.attrib.get("name")
        if name:
            metadata.append(name)
    descriptors = {
        path.stem: path.relative_to(snapshot).as_posix()
        for path in snapshot.glob("*/*.xml")
    }
    entries = []
    for name in metadata:
        object_name = name.split(".", 1)[-1]
        descriptor = descriptors.get(object_name)
        paths: list[str] = []
        if descriptor:
            object_root = snapshot / Path(descriptor).with_suffix("")
            paths = [descriptor]
            if object_root.is_dir():
                paths += sorted(
                    path.relative_to(snapshot).as_posix()
                    for path in object_root.rglob("*")
                    if path.is_file() and path.suffix.lower() in {".xml", ".bsl"}
                )
        entries.append({"metadata": name, "paths": paths})
    payload = {"version": 1, "entries": entries}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    emit({"action": "build-catalog", "entries": len(entries), "bytes": output.stat().st_size,
          "elapsedNs": time.perf_counter_ns() - started})


def query_catalog(catalog: Path, terms: list[str], limit: int) -> None:
    started = time.perf_counter_ns()
    entries = json.loads(catalog.read_text(encoding="utf-8"))["entries"]
    words = [word.casefold() for term in terms for word in re.findall(r"[\w]+", term)]
    ranked = []
    for entry in entries:
        haystack = (entry["metadata"] + " " + " ".join(entry["paths"])).casefold()
        score = sum(word in haystack for word in words)
        if score:
            ranked.append((score, entry["metadata"], entry))
    ranked.sort(key=lambda row: (-row[0], row[1]))
    results = [entry for _, _, entry in ranked[:limit]]
    emit({"action": "catalog-query", "terms": terms, "results": results,
          "elapsedNs": time.perf_counter_ns() - started})


def rg_search(snapshot: Path, pattern: str, glob: str | None, limit: int) -> None:
    rg = os.environ["ISSUE51_RG"]
    command = [rg, "--no-heading", "--line-number", "--color", "never"]
    if glob:
        command += ["--glob", glob]
    command += [pattern, str(snapshot)]
    started = time.perf_counter_ns()
    run = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    rows = run.stdout.splitlines()
    emit({"action": "rg", "pattern": pattern, "glob": glob, "returncode": run.returncode,
          "totalMatches": len(rows), "results": rows[:limit],
          "elapsedNs": time.perf_counter_ns() - started})


def read_source(snapshot: Path, relative: str, start: int, end: int) -> None:
    root = snapshot.resolve()
    path = (root / relative).resolve()
    if root not in path.parents or not path.is_file():
        raise SystemExit("path is outside snapshot or not a file")
    raw = path.read_bytes()
    lines = raw.decode("utf-8-sig", errors="replace").splitlines()
    selected = lines[start - 1:end]
    text = "\n".join(f"{number}|{line}" for number, line in enumerate(selected, start))
    emit({"action": "read", "path": relative, "start": start, "end": end,
          "fileBytes": len(raw), "contextBytes": len(text.encode()), "text": text})


async def mcp_call(url: str, tool: str, arguments: dict) -> None:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
    started = time.perf_counter_ns()
    async with streamablehttp_client(url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool, arguments)
    content = [getattr(item, "text", str(item)) for item in result.content]
    emit({"action": "mcp", "tool": tool, "arguments": arguments, "result": content,
          "elapsedNs": time.perf_counter_ns() - started})


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("build-catalog"); p.add_argument("snapshot", type=Path); p.add_argument("output", type=Path)
    p = sub.add_parser("catalog"); p.add_argument("catalog", type=Path); p.add_argument("terms", nargs="+"); p.add_argument("--limit", type=int, default=8)
    p = sub.add_parser("rg"); p.add_argument("snapshot", type=Path); p.add_argument("pattern"); p.add_argument("--glob"); p.add_argument("--limit", type=int, default=30)
    p = sub.add_parser("read"); p.add_argument("snapshot", type=Path); p.add_argument("path"); p.add_argument("start", type=int); p.add_argument("end", type=int)
    p = sub.add_parser("mcp"); p.add_argument("url"); p.add_argument("tool"); p.add_argument("arguments")
    args = parser.parse_args()
    if args.command == "build-catalog": build_catalog(args.snapshot, args.output)
    elif args.command == "catalog": query_catalog(args.catalog, args.terms, args.limit)
    elif args.command == "rg": rg_search(args.snapshot, args.pattern, args.glob, args.limit)
    elif args.command == "read": read_source(args.snapshot, args.path, args.start, args.end)
    else: asyncio.run(mcp_call(args.url, args.tool, json.loads(args.arguments)))


if __name__ == "__main__":
    main()
