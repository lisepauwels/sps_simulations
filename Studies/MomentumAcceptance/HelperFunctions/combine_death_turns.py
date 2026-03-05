"""
combine_death_turns.py
======================
Combines death_turns_*.json files from parallel job folders into a single
compressed output per "case" (i.e. per unique parameter combination).

The script is designed to be study-type agnostic: each study type is
described by a StudyConfig that specifies only *how to parse the filename*
and *how to build the output filename*.  The combining logic itself is
shared.

Supported study types (auto-detected from the folder name, or pass explicitly):
  - "error_variant"  : death_turns_{line_type}_{chroma}_{plane}.json
  - "chroma_scan"    : death_turns_xi_{xi_x}_{xi_y}_{plane}.json
                       (lives in qpx_zero / qpy_zero subfolders)
  - "tune_scan"      : death_turns_xi_{xi}_tune_{qx}_{qy}_{plane}.json
                       (lives in resonance_margin_scan / tune_mirror subfolders)

You can also register your own StudyConfig at runtime (see bottom of file).

Usage (CLI)
-----------
    python combine_death_turns.py <study_path> [--study-type TYPE]
                                  [--output-name PREFIX]
                                  [--result-path PATH] [--plot-path PATH]
                                  [--quiet]

Usage (Python)
--------------
    from combine_death_turns import combine_death_turns
    combine_death_turns("path/to/study", study_type="chroma_scan")
"""

from __future__ import annotations

import gzip
import json
import re
import argparse
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class StudyConfig:
    """Describes how to parse and name files for one study type.

    Attributes
    ----------
    name         : Registry key, e.g. "chroma_scan".
    pattern      : Regex with named groups matching the filename.
    output_stem  : Given the regex groupdict, returns the output filename stem.
    index_params : Parameters used as the primary index when loading results
                   (the "rows" of your data). E.g. ["xi_y"] for qpx_zero.
    plane_param  : Name of the regex group that holds the plane (default "plane").
    fixed_params : Parameters that are fixed for a given study folder and are
                   NOT part of the varying index. Used for display only.
    description  : Human-readable description.
    """
    name:         str
    pattern:      re.Pattern
    output_stem:  Callable[[dict], str]
    index_params: list[str]        = field(default_factory=list)
    plane_param:  str              = "plane"
    fixed_params: list[str]        = field(default_factory=list)
    description:  str              = ""


# ---------------------------------------------------------------------------
# Registry of study types
# ---------------------------------------------------------------------------

_REGISTRY: dict[str, StudyConfig] = {}


def register(config: StudyConfig) -> StudyConfig:
    _REGISTRY[config.name] = config
    return config


# --- error_variant ----------------------------------------------------------
register(StudyConfig(
    name="error_variant",
    pattern=re.compile(
        r"^death_turns_"
        r"(?P<line_type>.+)_"
        r"(?P<chroma>-?\d+(?:\.\d+)?)_"
        r"(?P<plane>DPpos|DPneg)"
        r"\.json$"
    ),
    output_stem=lambda g: f"death_turns_{g['line_type']}_{g['chroma']}_{g['plane']}",
    index_params=["chroma"],
    fixed_params=["line_type"],
    description="Error-variant scan: death_turns_{line_type}_{chroma}_{plane}.json",
))

# --- chroma_scan_qpx --------------------------------------------------------
# qpx_zero: xi_x is fixed at 0, xi_y varies
register(StudyConfig(
    name="chroma_scan_qpx",
    pattern=re.compile(
        r"^death_turns_xi_"
        r"(?P<xi_x>-?\d+(?:\.\d+)?)_"
        r"(?P<xi_y>-?\d+(?:\.\d+)?)_"
        r"(?P<plane>DPpos|DPneg)"
        r"\.json$"
    ),
    output_stem=lambda g: f"death_turns_xi_{g['xi_x']}_{g['xi_y']}_{g['plane']}",
    index_params=["xi_y"],
    fixed_params=["xi_x"],
    description="Chromaticity scan (qpx=0): death_turns_xi_{xi_x}_{xi_y}_{plane}.json",
))

# --- chroma_scan_qpy --------------------------------------------------------
# qpy_zero: xi_y is fixed at 0, xi_x varies
register(StudyConfig(
    name="chroma_scan_qpy",
    pattern=re.compile(
        r"^death_turns_xi_"
        r"(?P<xi_x>-?\d+(?:\.\d+)?)_"
        r"(?P<xi_y>-?\d+(?:\.\d+)?)_"
        r"(?P<plane>DPpos|DPneg)"
        r"\.json$"
    ),
    output_stem=lambda g: f"death_turns_xi_{g['xi_x']}_{g['xi_y']}_{g['plane']}",
    index_params=["xi_x"],
    fixed_params=["xi_y"],
    description="Chromaticity scan (qpy=0): death_turns_xi_{xi_x}_{xi_y}_{plane}.json",
))

# --- tune_scan --------------------------------------------------------------
register(StudyConfig(
    name="tune_scan",
    pattern=re.compile(
        r"^death_turns_xi_"
        r"(?P<xi>-?\d+(?:\.\d+)?)_tune_"
        r"(?P<qx>-?\d+(?:\.\d+)?)_"
        r"(?P<qy>-?\d+(?:\.\d+)?)_"
        r"(?P<plane>DPpos|DPneg)"
        r"\.json$"
    ),
    output_stem=lambda g: f"death_turns_xi_{g['xi']}_tune_{g['qx']}_{g['qy']}_{g['plane']}",
    index_params=["xi"],
    fixed_params=["qx", "qy"],
    description="Tune scan: death_turns_xi_{xi}_tune_{qx}_{qy}_{plane}.json",
))


# ---------------------------------------------------------------------------
# Auto-detect study type from folder name
# ---------------------------------------------------------------------------

_FOLDER_TO_STUDY_TYPE: dict[str, str] = {
    "qpx_zero":              "chroma_scan_qpx",
    "qpy_zero":              "chroma_scan_qpy",
    "resonance_margin_scan": "tune_scan",
    "tune_mirror":           "tune_scan",
}


def _detect_study_type(study_path: Path) -> str | None:
    """Try to infer the study type from the folder name."""
    return _FOLDER_TO_STUDY_TYPE.get(study_path.name)


# ---------------------------------------------------------------------------
# Core combining logic
# ---------------------------------------------------------------------------

def _merge_death_turn_files(file_list: list[Path]) -> dict:
    """Load and merge a list of death_turns JSON files."""
    combined: dict = {"sweep_per_turn": 0, "at_turn": []}
    for fp in file_list:
        with open(fp) as f:
            data = json.load(f)
        if combined["sweep_per_turn"] == 0:
            combined["sweep_per_turn"] = data["sweep_per_turn"]
        elif combined["sweep_per_turn"] != data["sweep_per_turn"]:
            raise ValueError(
                f"Inconsistent sweep_per_turn in {fp}: "
                f"expected {combined['sweep_per_turn']}, got {data['sweep_per_turn']}"
            )
        combined["at_turn"].extend(data["at_turn"])
    return combined


def combine_death_turns(
    study_path: str | Path,
    study_type: str | None = None,
    output_name: str | None = None,
    *,
    result_path: str | Path | None = None,
    plot_path: str | Path | None = None,
    verbose: bool = True,
) -> None:
    """
    Combine death_turns JSON files from job_* subfolders.

    Parameters
    ----------
    study_path  : Path to the folder containing job_* subfolders.
    study_type  : One of the registered study types (see _REGISTRY).
                  If None, auto-detection from the folder name is attempted.
    output_name : Optional prefix added to all output filenames.
    result_path : Where to write combined .json.gz files.
                  Defaults to <study_path>/../../results/
    plot_path   : Where to write plots (reserved for future use).
                  Defaults to <study_path>/../../plots/
    verbose     : Print progress information.
    """
    study_path = Path(study_path).resolve()

    # --- resolve output directories -----------------------------------------
    base = study_path.parents[1]   # two levels up: studies/<subfolder> -> studies -> parent
    result_path = Path(result_path).resolve() if result_path else base / "results"
    plot_path   = Path(plot_path).resolve()   if plot_path   else base / "plots"
    result_path.mkdir(parents=True, exist_ok=True)

    prefix = f"{output_name}_" if output_name else ""

    if verbose:
        print(f"Study path : {study_path}")
        print(f"Result path: {result_path}")

    # --- resolve study type -------------------------------------------------
    if study_type is None:
        study_type = _detect_study_type(study_path)
    if study_type is None:
        raise ValueError(
            f"Cannot detect study type from folder name '{study_path.name}'. "
            f"Pass study_type= explicitly. Available: {list(_REGISTRY)}"
        )
    if study_type not in _REGISTRY:
        raise ValueError(
            f"Unknown study type '{study_type}'. Available: {list(_REGISTRY)}"
        )

    config = _REGISTRY[study_type]
    if verbose:
        print(f"Study type : {study_type}  ({config.description})")

    # --- group files by case key --------------------------------------------
    groups: dict[tuple, list[Path]] = defaultdict(list)
    all_files = list(study_path.glob("job_*/death_turns_*.json"))

    if not all_files:
        if verbose:
            print("No death_turns files found — nothing to do.")
        return

    if verbose:
        print(f"Found {len(all_files)} JSON files across job folders")

    skipped = 0
    for fp in all_files:
        m = config.pattern.match(fp.name)
        if not m:
            skipped += 1
            continue
        groups[tuple(sorted(m.groupdict().items()))].append(fp)

    if skipped and verbose:
        print(f"  Skipped {skipped} files that did not match the pattern")

    # --- combine and write --------------------------------------------------
    for key_items, file_list in groups.items():
        groupdict = dict(key_items)
        stem = config.output_stem(groupdict)
        out_file = result_path / f"{prefix}{stem}.json.gz"

        if verbose:
            print(f"  {stem}  ({len(file_list)} files) -> {out_file.name}")

        combined = _merge_death_turn_files(file_list)

        with gzip.open(out_file, "wt", encoding="utf-8") as f:
            json.dump(combined, f)

    if verbose:
        print(f"Done. Wrote {len(groups)} combined files to {result_path}")


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

def load_death_turns(
    result_path: str | Path,
    study_type: str,
    output_name: str | None = None,
    *,
    index_params: list[str] | None = None,
    cast_index: bool = True,
    verbose: bool = True,
) -> dict[Any, dict[str, dict]]:
    """
    Load combined death_turns .json.gz files from result_path into a nested dict.

    The returned structure is::

        {
            index_value : {
                "DPpos": {"sweep_per_turn": ..., "at_turn": [...]},
                "DPneg": {"sweep_per_turn": ..., "at_turn": [...]},
            },
            ...
        }

    For multi-parameter indices (e.g. tune_scan with qx and qy), index_value
    is a tuple: ``(qx_value, qy_value)``.

    Parameters
    ----------
    result_path  : Folder containing the combined .json.gz files.
    study_type   : One of the registered study types (see _REGISTRY).
    output_name  : Prefix that was used when combining (passed to combine_death_turns).
    index_params : Override the index_params from the StudyConfig. Useful e.g.
                   for qpy_zero where xi_x varies instead of xi_y.
    cast_index   : If True (default), convert numeric index values to float.
                   Set to False to keep them as strings.
    verbose      : Print progress information.

    Returns
    -------
    Nested dict keyed first by index value (or tuple of values), then by plane.

    Examples
    --------
    Load qpx_zero results (xi_y varies):

        data = load_death_turns("path/to/results", "chroma_scan",
                                output_name="qpx_zero")
        at_turn_pos = data[1.5]["DPpos"]["at_turn"]

    Load qpy_zero results (xi_x varies — override index_params):

        data = load_death_turns("path/to/results", "chroma_scan",
                                output_name="qpy_zero",
                                index_params=["xi_x"])

    Load tune_scan (two-parameter index):

        data = load_death_turns("path/to/results", "tune_scan")
        at_turn = data[(62.31, 60.32)]["DPpos"]["at_turn"]
    """
    result_path = Path(result_path).resolve()

    if study_type not in _REGISTRY:
        raise ValueError(
            f"Unknown study type '{study_type}'. Available: {list(_REGISTRY)}"
        )
    config = _REGISTRY[study_type]

    # Allow caller to override which params form the index
    _index_params = index_params if index_params is not None else config.index_params
    if not _index_params:
        raise ValueError(
            f"No index_params defined for study type '{study_type}'. "
            "Pass index_params= explicitly."
        )

    prefix = f"{output_name}_" if output_name else ""
    # Match the combined output files using the same pattern
    files = list(result_path.glob(f"{prefix}death_turns_*.json.gz"))

    if not files:
        raise FileNotFoundError(
            f"No combined death_turns files found in {result_path} "
            f"with prefix '{prefix}'"
        )

    if verbose:
        print(f"Loading {len(files)} files from {result_path}")

    def _cast(val: str) -> Any:
        if not cast_index:
            return val
        try:
            return float(val)
        except ValueError:
            return val

    results: dict[Any, dict[str, dict]] = defaultdict(dict)

    for fp in sorted(files):
        # Strip the prefix and .json.gz to get the stem the pattern was built for
        stem = fp.name[len(prefix):]          # remove output_name prefix
        stem = stem.removesuffix(".gz")       # -> death_turns_...json
        m = config.pattern.match(stem)
        if not m:
            continue
        g = m.groupdict()

        plane = g[config.plane_param]

        # Build the index key
        raw_index = [g[p] for p in _index_params]
        index_key = (
            _cast(raw_index[0]) if len(raw_index) == 1
            else tuple(_cast(v) for v in raw_index)
        )

        with gzip.open(fp, "rt", encoding="utf-8") as f:
            data = json.load(f)

        results[index_key][plane] = data
        if verbose:
            print(f"  {index_key!r:30s}  {plane}")

    # Sort by index key for convenience
    try:
        sorted_results = dict(sorted(results.items()))
    except TypeError:
        sorted_results = dict(results)   # unsortable keys (mixed types), leave as-is

    if verbose:
        print(f"Loaded {len(sorted_results)} index values, "
              f"planes per value: {set(len(v) for v in sorted_results.values())}")

    return sorted_results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("study_path", help="Path to the folder containing job_* subfolders")
    p.add_argument(
        "--study-type", default=None,
        choices=list(_REGISTRY),
        help="Study type (auto-detected from folder name if not given)",
    )
    p.add_argument("--output-name", default=None, help="Prefix for output filenames")
    p.add_argument("--result-path", default=None, help="Directory for output files")
    p.add_argument("--plot-path",   default=None, help="Directory for plots (future use)")
    p.add_argument("--quiet", action="store_true", help="Suppress progress output")
    return p


if __name__ == "__main__":
    args = _build_parser().parse_args()
    combine_death_turns(
        study_path=args.study_path,
        study_type=args.study_type,
        output_name=args.output_name,
        result_path=args.result_path,
        plot_path=args.plot_path,
        verbose=not args.quiet,
    )