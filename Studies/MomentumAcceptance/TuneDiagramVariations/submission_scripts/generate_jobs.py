#!/usr/bin/env python3
from __future__ import annotations

import io
import argparse
import itertools
import math
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from ruamel.yaml import YAML
yaml = YAML(typ='safe')


def load_cases(file):
    if isinstance(file, io.IOBase):
        cases = yaml.load(file)
    else:
        file = Path(file).resolve()
        with file.open('r') as fid:
            cases = yaml.load(fid)

    if not isinstance(cases, dict):
        raise ValueError("Job specification must be a mapping of case_name -> list of entries")

    # YAML order is preserved, but keep it explicit/readable
    ordered = OrderedDict()
    for k, v in cases.items():
        ordered[k] = v
    return ordered


def product_count(arg_lists: List[List[Any]]) -> int:
    c = 1
    for lst in arg_lists:
        c *= len(lst)
    return c


def iter_combos(arg_lists: List[List[Any]]) -> Iterable[Tuple[Any, ...]]:
    return itertools.product(*arg_lists)


def validate_cases(cases: "OrderedDict[str, List[Dict[str, Any]]]") -> None:
    for case, entries in cases.items():
        if not isinstance(entries, list) or not entries:
            raise ValueError(f"Case '{case}' must be a non-empty list")

        for i, e in enumerate(entries):
            if "runfile" not in e or "args" not in e or "num_jobs" not in e:
                raise ValueError(
                    f"Case '{case}' entry #{i} must contain runfile, args, num_jobs"
                )
            if not isinstance(e["args"], list) or any(not isinstance(x, list) for x in e["args"]):
                raise ValueError(f"Case '{case}' entry #{i}: 'args' must be a list of lists")
            if any(["$JOBID" in [str(xx).upper() for xx in x] and len(x) > 1 for x in e["args"]]):
                raise ValueError(f"Case '{case}' entry #{i}: $JobID must be the only element in an args list")
            nj = int(e["num_jobs"])
            if nj <= 0:
                raise ValueError(f"Case '{case}' entry #{i}: num_jobs must be > 0")


def summarise(cases: "OrderedDict[str, List[Dict[str, Any]]]", case_order: List[str]) -> Dict[str, Any]:
    per_case = {}
    total_lines = 0
    max_steps = 0

    for case in case_order:
        entries = cases[case]
        case_lines = 0
        case_steps = 0

        entry_summaries = []
        for e in entries:
            nj = int(e["num_jobs"])
            ncomb = product_count(e["args"])
            lines = nj * ncomb
            case_lines += lines
            case_steps = max(case_steps, nj)
            entry_summaries.append(
                {
                    "runfile": e["runfile"],
                    "num_jobs": nj,
                    "combos_per_step": ncomb,
                    "lines": lines,
                }
            )

        per_case[case] = {
            "max_step": case_steps - 1,
            "num_steps": case_steps,
            "entries": entry_summaries,
            "lines": case_lines,
        }
        total_lines += case_lines
        max_steps = max(max_steps, case_steps)

    return {"per_case": per_case, "total_lines": total_lines, "max_steps": max_steps}


def write_jobs_list(
    cases: "OrderedDict[str, List[Dict[str, Any]]]",
    case_order: List[str],
    out_path: Path,
) -> None:
    # Interleave by step, then by case, then by entry, then by cartesian combo
    max_steps = 0
    for case in case_order:
        for e in cases[case]:
            max_steps = max(max_steps, int(e["num_jobs"]))

    with out_path.open("w") as out:
        for step in range(max_steps):
            for case in case_order:
                for e in cases[case]:
                    nj = int(e["num_jobs"])
                    if step >= nj:
                        continue
                    runfile = str(e["runfile"])
                    for combo in iter_combos(e["args"]):
                        fields = [case, str(step), runfile, *map(str, combo)]
                        fields = [str(step) if f.upper() == '$JOBID' else f for f in fields]
                        out.write(" ".join(fields) + "\n")


def head_tail(path: Path, n: int = 5) -> Tuple[List[str], List[str]]:
    # Simple, memory-safe preview
    head = []
    with path.open("r") as f:
        for _ in range(n):
            line = f.readline()
            if not line:
                break
            head.append(line.rstrip("\n"))

    # Tail: read last ~64kB (good enough for huge files)
    tail = []
    with path.open("rb") as f:
        f.seek(0, 2)
        size = f.tell()
        chunk = 65536
        f.seek(max(0, size - chunk))
        data = f.read().decode(errors="replace").splitlines()
        tail = data[-n:] if len(data) >= n else data

    return head, tail


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate HTCondor jobs.list from a YAML spec.")
    ap.add_argument("--spec", required=True, help="YAML spec file")
    ap.add_argument("--out", default="jobs.list", help="Output file (default: jobs.list)")
    ap.add_argument(
        "--case-order",
        default="",
        help="Comma-separated case order (default: YAML order)",
    )
    ap.add_argument(
        "--preview",
        action="store_true",
        help="After writing, print first/last few lines",
    )
    ap.add_argument(
        "--preview-lines",
        type=int,
        default=8,
        help="How many lines to show for --preview (default: 8)",
    )
    args = ap.parse_args()

    spec_path = Path(args.spec)
    out_path = Path(args.out)

    cases = load_cases(spec_path)
    validate_cases(cases)

    if args.case_order.strip():
        case_order = [c.strip() for c in args.case_order.split(",") if c.strip()]
        missing = [c for c in case_order if c not in cases]
        if missing:
            raise SystemExit(f"Unknown case(s) in --case-order: {missing}")
    else:
        case_order = list(cases.keys())

    info = summarise(cases, case_order)

    # Pretty-ish summary
    print(f"Spec: {spec_path}")
    print("Case order:", ", ".join(case_order))
    for case, cd in info["per_case"].items():
        print(f"[{case}]")
        print(f"  steps: {cd['num_steps']} (0..{cd['max_step']})")
        for e in cd["entries"]:
            print(
                f"  - {e['runfile']}: num_jobs={e['num_jobs']}, "
                f"combos/step={e['combos_per_step']}, lines={e['lines']}"
            )
        print(f"  total lines for case: {cd['lines']}")
    print(f"TOTAL lines: {info['total_lines']}")
    print(f"Max steps across cases: {info['max_steps']}")

    write_jobs_list(cases, case_order, out_path)
    print(f"Wrote: {out_path}")

    if args.preview:
        h, t = head_tail(out_path, n=args.preview_lines)
        print("\n--- HEAD ---")
        for line in h:
            print(line)
        print("--- TAIL ---")
        for line in t:
            print(line)


if __name__ == "__main__":
    main()
