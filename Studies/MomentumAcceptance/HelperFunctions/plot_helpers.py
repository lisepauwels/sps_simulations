import numpy as np
import matplotlib.pyplot as plt
import colorsys

def generate_distinct_dashes(
    n: int,
    *,
    min_on: float = 1.0,
    max_on: float = 10.0,
    min_off: float = 1.0,
    max_off: float = 10.0,
    include_solid: bool = True,
):
    """
    Generate `n` visually distinct linestyles for Matplotlib.

    Returns a list of linestyles usable as `linestyle=...` in ax.plot:
      - "-" for solid (optional)
      - dash tuples of the form (offset, (on, off, on, off, ...))

    The patterns are built from a small set of base "motifs" and scaled/offset
    so they remain distinguishable without becoming too chaotic.
    """
    if n <= 0:
        return []

    styles = []
    if include_solid:
        styles.append("-")
        if n == 1:
            return styles
        n_remaining = n - 1
    else:
        n_remaining = n

    # Base motifs: dashed, dotted, dash-dot, long-short, etc.
    motifs = [
        (1, 1),           # dotted
        (2, 2),           # short dashed
        (3, 2),           # medium dash
        (4, 2),           # longer dash
        (6, 3),           # long dash
        (3, 1, 1, 1),     # dash-dot (tight)
        (5, 2, 1, 2),     # dash-dot (looser)
        (6, 2, 2, 2),     # long-short
        (1, 2),           # sparse dots
        (2, 1),           # dense dashes
        (8, 2),           # very long dash
        (2, 2, 6, 2),     # two-dash motif
    ]

    # Choose scale factors so patterns spread out but stay readable
    # Use a quasi-log spacing (helps keep early patterns distinct).
    scales = np.geomspace(1.0, 2.5, num=max(1, int(np.ceil(n_remaining / len(motifs)))))
    offsets = np.linspace(0.0, 6.0, num=max(2, int(np.ceil(n_remaining / 3))))  # small phase offsets

    def clamp(v, lo, hi):
        return float(np.clip(v, lo, hi))

    k = 0
    for s in scales:
        for motif in motifs:
            if k >= n_remaining:
                break

            # Scale motif and clamp to keep it within sensible dash lengths
            scaled = []
            for i, v in enumerate(motif):
                if i % 2 == 0:  # "on"
                    scaled.append(clamp(v * s, min_on, max_on))
                else:           # "off"
                    scaled.append(clamp(v * s, min_off, max_off))

            offset = float(offsets[k % len(offsets)])
            styles.append((offset, tuple(scaled)))
            k += 1

        if k >= n_remaining:
            break

    return styles

def random_distinct_colors(n, seed=None):
    rng = np.random.default_rng(seed)

    hues = np.linspace(0, 1, n, endpoint=False)
    rng.shuffle(hues)

    colors = []
    for h in hues:
        s = rng.uniform(0.6, 0.9)
        v = rng.uniform(0.7, 0.95)
        colors.append(colorsys.hsv_to_rgb(h, s, v))

    return colors