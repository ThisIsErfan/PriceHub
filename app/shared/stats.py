"""Shared statistics helpers used by the technical stats + reports endpoints."""

from __future__ import annotations

import statistics
from decimal import Decimal
from typing import Any, Optional


def money(x: Any) -> Optional[str]:
    """Quantize a numeric to 2 dp and return it as a string (matches the price
    fields elsewhere in the feed). None stays None."""
    if x is None:
        return None
    return str(Decimal(str(round(float(x), 2))))


def side_stats(
    vals: list[float],
) -> tuple[Optional[dict[str, Any]], Optional[float], Optional[float]]:
    """Summary stats for one series. Returns (block, mean, median); block is None
    when there are no values. `mean_Nsigma` drops values beyond ±Nσ of the mean,
    then re-averages (single-pass sigma clip)."""
    if not vals:
        return None, None, None
    mean = statistics.fmean(vals)
    median = statistics.median(vals)
    std = statistics.pstdev(vals) if len(vals) > 1 else 0.0

    def trimmed_mean(k: float):
        if std == 0:
            return mean, len(vals)
        kept = [v for v in vals if abs(v - mean) <= k * std]
        return (statistics.fmean(kept), len(kept)) if kept else (None, 0)

    m2, c2 = trimmed_mean(2)
    m3, c3 = trimmed_mean(3)
    block = {
        "sample_count": len(vals),
        "min": money(min(vals)),
        "max": money(max(vals)),
        "mean": money(mean),
        "median": money(median),
        "stdev": money(std),
        "mean_2sigma": money(m2),
        "count_2sigma": c2,
        "mean_3sigma": money(m3),
        "count_3sigma": c3,
    }
    return block, mean, median
