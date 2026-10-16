"""Evidence pillar: a scripted protocol gives ground truth, a log makes it replayable.

Protocol: the driver looks at the road and blinks normally, and on a high beep
closes their eyes until the low beep. The cue windows are the ground truth for
"eyes deliberately closed" (a stand-in for a microsleep that is safe to act out).
"""
import csv
import math
import random
from dataclasses import dataclass

from .features import Observation
from .monitor import MICROSLEEP, Config, Monitor

LOG_FIELDS = ["t", "face", "ear", "ear_l", "ear_r", "mar", "yaw", "pitch",
              "proc_ms", "gt", "recalib", "level", "alerts"]
GT_NONE, GT_OPEN, GT_CLOSED = -1, 0, 1


@dataclass
class Protocol:
    trials: int = 8
    close_s: float = 2.0
    open_min_s: float = 4.0
    open_max_s: float = 7.0
    seed: int = 7

    def __post_init__(self):
        rng = random.Random(self.seed)
        self.segments = []  # (start, end, gt) relative to protocol start
        t = 0.0
        for _ in range(self.trials):
            open_s = rng.uniform(self.open_min_s, self.open_max_s)
            self.segments.append((t, t + open_s, GT_OPEN))
            t += open_s
            self.segments.append((t, t + self.close_s, GT_CLOSED))
            t += self.close_s
        self.segments.append((t, t + self.open_max_s, GT_OPEN))
        self.duration = t + self.open_max_s

    def gt_at(self, elapsed):
        for start, end, gt in self.segments:
            if start <= elapsed < end:
                return gt
        return GT_NONE


# ---- log io ---------------------------------------------------------------
def read_log(path):
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    out = []
    for r in rows:
        out.append({
            "t": float(r["t"]), "face": r["face"] == "1",
            "ear": float(r["ear"]), "ear_l": float(r["ear_l"]), "ear_r": float(r["ear_r"]),
            "mar": float(r["mar"]), "yaw": float(r["yaw"]), "pitch": float(r["pitch"]),
            "proc_ms": float(r["proc_ms"]), "gt": int(r["gt"]), "recalib": r["recalib"] == "1",
        })
    return out


def replay(rows, cfg=None):
    """Run the monitor over logged features. Returns (monitor, per-row reports)."""
    mon = Monitor(cfg or Config())
    reports = []
    for r in rows:
        if r["recalib"]:
            mon.reset()
        obs = None
        if r["face"]:
            obs = Observation(r["ear"], r["ear_l"], r["ear_r"], r["mar"], r["yaw"], r["pitch"])
        reports.append(mon.update(r["t"], obs))
    return mon, reports


# ---- metrics --------------------------------------------------------------
def gt_intervals(rows):
    """Contiguous runs of GT_CLOSED as (start, end)."""
    out, start = [], None
    for r in rows:
        if r["gt"] == GT_CLOSED and start is None:
            start = r["t"]
        elif r["gt"] != GT_CLOSED and start is not None:
            out.append((start, r["t"]))
            start = None
    if start is not None:
        out.append((start, rows[-1]["t"]))
    return out


def score(rows, mon, reports, slack_s=0.5):
    """Event and frame metrics over the part of the log that ran the protocol.

    slack_s: allowance for human reaction to the beep; frames that close to a
    cue boundary are left out of the frame metrics, and an alarm up to slack_s
    after the cue window still counts as a hit.
    """
    proto = [i for i, r in enumerate(rows) if r["gt"] != GT_NONE]
    if not proto:
        return None
    t0, t1 = rows[proto[0]]["t"], rows[proto[-1]]["t"]
    windows = gt_intervals([rows[i] for i in proto])
    alarms = [e for e in mon.events if e.kind == MICROSLEEP and t0 <= e.alarm <= t1 + slack_s]

    hits, latencies = 0, []
    matched = set()
    for gs, ge in windows:
        inside = [e for e in alarms if gs <= e.alarm <= ge + slack_s]
        if inside:
            hits += 1
            latencies.append(inside[0].alarm - gs)
            matched.update(id(e) for e in inside)
    false_alarms = [e for e in alarms if id(e) not in matched]
    open_minutes = ((t1 - t0) - sum(ge - gs for gs, ge in windows)) / 60.0

    boundaries = [b for w in windows for b in w]
    tp = fp = fn = tn = 0
    for i in proto:
        t = rows[i]["t"]
        if any(abs(t - b) < slack_s for b in boundaries):
            continue
        rep = reports[i]
        if rep["state"] != "OK":
            continue
        gt, pred = rows[i]["gt"] == GT_CLOSED, rep["closed"]
        tp += gt and pred
        fp += (not gt) and pred
        fn += gt and not pred
        tn += (not gt) and not pred

    return {
        "trials": len(windows),
        "hits": hits,
        "recall": hits / len(windows) if windows else math.nan,
        "false_alarms": len(false_alarms),
        "false_alarms_per_min": len(false_alarms) / open_minutes if open_minutes > 0 else math.nan,
        "latency_mean_s": sum(latencies) / len(latencies) if latencies else math.nan,
        "latency_max_s": max(latencies) if latencies else math.nan,
        "frame_precision": tp / (tp + fp) if tp + fp else math.nan,
        "frame_recall": tp / (tp + fn) if tp + fn else math.nan,
        "frame_accuracy": (tp + tn) / (tp + tn + fp + fn) if tp + tn + fp + fn else math.nan,
        "frames_scored": tp + tn + fp + fn,
    }


def timing(rows):
    ms = sorted(r["proc_ms"] for r in rows)
    span = rows[-1]["t"] - rows[0]["t"] if len(rows) > 1 else math.nan
    return {
        "fps": (len(rows) - 1) / span if span and span > 0 else math.nan,
        "proc_ms_p50": ms[len(ms) // 2],
        "proc_ms_p95": ms[min(len(ms) - 1, int(0.95 * len(ms)))],
        "face_found": sum(r["face"] for r in rows) / len(rows),
    }
