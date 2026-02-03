import json
import numpy as np
from datetime import date, datetime
from collections.abc import Mapping


def coerce_key(s: str):
    # Try int first
    try:
        return int(s)
    except ValueError:
        pass
    # Then float, if you have float-like keys
    try:
        return float(s)
    except ValueError:
        return s

def object_hook_convert_numeric_keys(d):
    out = {}
    for k, v in d.items():
        if isinstance(k, str):
            out[coerce_key(k)] = v
        else:
            out[k] = v
    return out


class NumpyFriendlyEncoder(json.JSONEncoder):
    """Normalises numpy scalars/arrays and datetimes in BOTH keys and values."""

    def _coerce_scalar(self, obj):
        # Values used for both keys and values
        if isinstance(obj, np.bool_):
            return bool(obj)
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return obj

    def _convert_key(self, k):
        k = self._coerce_scalar(k)
        # Keep keys as JSON-legal primitives where possible; else stringify
        if isinstance(k, (str, int, float, bool)) or k is None:
            return k
        return str(k)

    def _normalise(self, o):
        if isinstance(o, Mapping):
            return {self._convert_key(k): self._normalise(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [self._normalise(v) for v in o]
        if isinstance(o, np.ndarray):
            return o.tolist()
        return self._coerce_scalar(o)

    # Ensure values that still reach default() are handled consistently
    def default(self, obj):
        coerced = self._coerce_scalar(obj)
        if coerced is not obj:
            return coerced
        return super().default(obj)

    def iterencode(self, o):
        return super().iterencode(self._normalise(o))
