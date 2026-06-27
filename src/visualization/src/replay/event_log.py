"""
Forward simulation of QQEMOD_aVWAP anchor discovery.

The full-dataset indicator CSV has the zone labels already (no lookahead — QQE is
backward-looking). This module replays the anchor-finding logic from aVWAP.py bar-by-bar
so the replay can show exactly which aVWAP lines would have been visible at each point
in time, respecting the max_anchors trimming window.

Zone boundary model (matches aVWAP.py find_qqemod_segments):
    A bear "meta-zone" starts when bear[i] first becomes True after a bull period,
    and ends when bull[j] first becomes True. Neutral bars (neither bear nor bull)
    between bear and bull are INCLUDED in the span and in the anchor search.
    The anchor (argmin Low or argmax High) is committed only when the opposite zone
    starts — i.e., "we didn't know the final anchor until the zone closed."

Lookahead addressed here:
    max_anchors trimming — at bar N the full-dataset CSV shows the last N anchors
    from the full history, but mid-dataset only the last N anchors up to bar N should
    be shown.

Lookahead NOT addressed (negligible):
    Zone labels (QQE1_Above_Upper, etc.) — backward-looking RSI/ATR computation.
    Anchor value (argmin/argmax) — backward-looking, committed once zone ends.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np
import pandas as pd


@dataclass
class AnchorEvent:
    anchor_bar: int         # row index of price extremum (argmin Low or argmax High)
    direction: str          # 'bear_dot' | 'bull_dot' | 'bear' | 'bull'
    cfg_idx: int            # QQEMOD config index (typically 0)
    add_bar: int            # replay bar at which this anchor first becomes visible
    remove_bar: Optional[int] = None  # bar at which it is trimmed; None = still active


def simulate_qqemod_avwap(
    df: pd.DataFrame,
    cfg_idx: int = 0,
    max_anchors: Optional[int] = 5,
    enabled: Optional[Dict[str, bool]] = None,
) -> List[AnchorEvent]:
    """
    Forward simulation of QQEMOD_aVWAP anchor discovery.

    Zone-close logic: a bear meta-zone runs from when bear first appears (after bull)
    until bull next appears. Neutral bars are part of the zone. The anchor
    (argmin Low / argmax High over the full zone span) is committed when the opposite
    zone starts — matching aVWAP.py's find_qqemod_segments() behavior.

    Args:
        enabled: dict controlling which anchor types to simulate, e.g.
                 {'bear_dot': True, 'bull_dot': True, 'bear': False, 'bull': False}
                 Keys map to QQEMOD_params: bear_dot=peak_to_peak,
                 bull_dot=valley_to_valley, bear=peak_to_valley, bull=valley_to_peak.
                 If None, all four types are enabled.
    """
    # Detect zone column names (try _c{N} suffix first, then unsuffixed)
    def _col(base: str) -> str:
        suffixed = f'{base}_c{cfg_idx}'
        return suffixed if suffixed in df.columns else base

    bull_col = _col('QQE1_Above_Upper')
    bear_col = _col('QQE1_Below_Lower')
    thresh_above_col = _col('QQE2_Above_Threshold')
    thresh_below_col = _col('QQE2_Below_Threshold')
    tl_col = _col('QQE2_Above_TL')

    if bull_col not in df.columns:
        return []

    bull = (
        df[bull_col].fillna(False).values.astype(bool)
        & df[thresh_above_col].fillna(False).values.astype(bool)
        & df[tl_col].fillna(False).values.astype(bool)
    )
    bear = (
        df[bear_col].fillna(False).values.astype(bool)
        & df[thresh_below_col].fillna(False).values.astype(bool)
        & ~df[tl_col].fillna(False).values.astype(bool)
    )

    high = df['high'].values if 'high' in df.columns else df['High'].values
    low = df['low'].values if 'low' in df.columns else df['Low'].values

    n = len(df)

    # Which anchor types to produce — driven by ind_conf, not by CSV column presence
    _default_enabled: Dict[str, bool] = {
        'bear_dot': True, 'bull_dot': True, 'bear': True, 'bull': True,
    }
    has: Dict[str, bool] = {k: (enabled or _default_enabled).get(k, False) for k in _default_enabled}

    events: List[AnchorEvent] = []
    active: Dict[str, List[AnchorEvent]] = {k: [] for k in has}

    # State: start of the current meta-zone (None = no active meta-zone)
    # A bear meta-zone starts when bear first appears (after bull or at start),
    # ends when bull next appears.  Vice versa for bull.
    bear_zone_start: Optional[int] = 0 if bear[0] else None
    bull_zone_start: Optional[int] = 0 if bull[0] else None

    def _commit_bear(zone_end: int) -> None:
        """Bear meta-zone just ended at zone_end (exclusive). Anchor = argmin Low in span."""
        if bear_zone_start is None:
            return
        anchor = bear_zone_start + int(np.argmin(low[bear_zone_start:zone_end]))
        for direction in ('bear_dot', 'bear'):
            if not has[direction]:
                continue
            ev = AnchorEvent(anchor_bar=anchor, direction=direction,
                             cfg_idx=cfg_idx, add_bar=zone_end)
            active[direction].append(ev)
            events.append(ev)
            if max_anchors is not None and len(active[direction]) > max_anchors:
                removed = active[direction].pop(0)
                removed.remove_bar = zone_end

    def _commit_bull(zone_end: int) -> None:
        """Bull meta-zone just ended at zone_end (exclusive). Anchor = argmax High in span."""
        if bull_zone_start is None:
            return
        anchor = bull_zone_start + int(np.argmax(high[bull_zone_start:zone_end]))
        for direction in ('bull_dot', 'bull'):
            if not has[direction]:
                continue
            ev = AnchorEvent(anchor_bar=anchor, direction=direction,
                             cfg_idx=cfg_idx, add_bar=zone_end)
            active[direction].append(ev)
            events.append(ev)
            if max_anchors is not None and len(active[direction]) > max_anchors:
                removed = active[direction].pop(0)
                removed.remove_bar = zone_end

    for i in range(1, n):
        prev_bear, prev_bull = bear[i - 1], bull[i - 1]
        cur_bear, cur_bull = bear[i], bull[i]

        # Bull zone STARTS → closes any open bear meta-zone, opens bull meta-zone
        if cur_bull and not prev_bull:
            _commit_bear(zone_end=i)
            bear_zone_start = None
            if bull_zone_start is None:
                bull_zone_start = i

        # Bear zone STARTS → closes any open bull meta-zone, opens bear meta-zone
        if cur_bear and not prev_bear:
            _commit_bull(zone_end=i)
            bull_zone_start = None
            if bear_zone_start is None:
                bear_zone_start = i

    return events


def active_at(events: List[AnchorEvent], bar: int, direction: str) -> List[AnchorEvent]:
    """Anchors of given direction active at `bar`, sorted oldest-to-newest anchor_bar."""
    result = [
        e for e in events
        if e.direction == direction
        and e.add_bar <= bar
        and (e.remove_bar is None or e.remove_bar > bar)
    ]
    return sorted(result, key=lambda e: e.anchor_bar)
