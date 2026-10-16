"""Replay a session log through the monitor and report the evidence.

    python evaluate.py logs/session-....csv            # metrics + threshold sweep
    python evaluate.py logs/session-....csv --plot out.png

The log stores raw features, not decisions, so any threshold can be re-tested
on the same recording without re-running the camera.
"""
import argparse
import math
from dataclasses import replace

from dms.evaluation import GT_CLOSED, read_log, replay, score, timing
from dms.monitor import MICROSLEEP, Config


def fmt(x, spec):
    return "-" if x is None or (isinstance(x, float) and math.isnan(x)) else format(x, spec)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("log")
    ap.add_argument("--plot", help="save an EAR timeline PNG")
    args = ap.parse_args()

    rows = read_log(args.log)
    tm = timing(rows)
    print(f"{len(rows)} frames, {rows[-1]['t'] - rows[0]['t']:.1f} s, {tm['fps']:.1f} FPS")
    print(f"processing per frame: p50 {tm['proc_ms_p50']:.1f} ms, p95 {tm['proc_ms_p95']:.1f} ms")
    print(f"face found in {tm['face_found']:.1%} of frames")

    base = Config()
    mon, reps = replay(rows, base)
    print(f"calibrated EAR baseline {fmt(mon.ear0, '.3f')}, variation {fmt(mon.calib_cv * 100, '.0f')}% "
          f"-> close below {fmt(mon.close_thr, '.3f')}, open above {fmt(mon.open_thr, '.3f')}")
    kinds = {}
    for e in mon.events:
        kinds[e.kind] = kinds.get(e.kind, 0) + 1
    print("events:", ", ".join(f"{k} x{n}" for k, n in kinds.items()) or "none")

    s = score(rows, mon, reps)
    if not s:
        print("\nNo protocol in this log (run with --protocol or press p) - nothing to score.")
    else:
        print(f"\nProtocol, default config (close_ratio {base.close_ratio}, microsleep {base.microsleep_s} s):")
        print(f"  closures alarmed      {s['hits']}/{s['trials']} (recall {s['recall']:.0%})")
        print(f"  false alarms          {s['false_alarms']} ({fmt(s['false_alarms_per_min'], '.2f')}/min of eyes-open time)")
        print(f"  alarm latency         mean {fmt(s['latency_mean_s'], '.2f')} s, max {fmt(s['latency_max_s'], '.2f')} s "
              f"(from cue; includes human reaction + {base.microsleep_s} s rule)")
        print(f"  frame eye state       precision {fmt(s['frame_precision'], '.2f')}, recall {fmt(s['frame_recall'], '.2f')}, "
              f"accuracy {fmt(s['frame_accuracy'], '.2f')} over {s['frames_scored']} frames")

        print("\nSweep (same recording):")
        print("  close_ratio  microsleep_s  recall  false/min  latency_s")
        for ratio in (0.5, 0.6, 0.7, 0.8):
            for ms in (0.5, 1.0, 1.5):
                cfg = replace(base, close_ratio=ratio, open_ratio=max(ratio + 0.1, base.open_ratio), microsleep_s=ms)
                m, r = replay(rows, cfg)
                sc = score(rows, m, r)
                mark = "  <- default" if (ratio, ms) == (base.close_ratio, base.microsleep_s) else ""
                print(f"  {ratio:>11.1f}  {ms:>12.1f}  {sc['recall']:>6.0%}  {fmt(sc['false_alarms_per_min'], '>9.2f')}"
                      f"  {fmt(sc['latency_mean_s'], '>9.2f')}{mark}")

    if args.plot:
        plot(rows, reps, mon, args.plot)
        print(f"\nplot: {args.plot}")


def plot(rows, reps, mon, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    t = [r["t"] for r in rows]
    fig, ax = plt.subplots(figsize=(12, 3.6))
    start = None
    for r in rows + [{"t": rows[-1]["t"], "gt": -1}]:
        if r["gt"] == GT_CLOSED and start is None:
            start = r["t"]
        elif r["gt"] != GT_CLOSED and start is not None:
            ax.axvspan(start, r["t"], color="#c83538", alpha=0.12, lw=0)
            start = None
    ax.plot(t, [r["ear"] for r in rows], color="#2e548a", lw=1, label="EAR")
    if mon.calibrated:
        ax.axhline(mon.close_thr, color="#c83538", lw=1, ls="--", label="close threshold")
        ax.axhline(mon.open_thr, color="#e08a00", lw=1, ls=":", label="open threshold")
    for e in mon.events:
        if e.kind == MICROSLEEP:
            ax.axvline(e.alarm, color="#c83538", lw=1.5)
    ax.set_xlabel("time (s)  ·  shaded: cue 'close eyes'  ·  red lines: microsleep alarm")
    ax.set_ylabel("EAR")
    ax.legend(loc="upper right", frameon=False, ncol=3)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=130)


if __name__ == "__main__":
    main()
