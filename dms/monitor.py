"""Driver state from a stream of observations. No camera code here, so the same
logic runs live, replays a CSV log, and runs in tests.

Uncertainty pillar: thresholds are per driver (calibrated), eye state uses
hysteresis, and the monitor says UNCERTAIN instead of guessing when the head is
turned too far for EAR to mean anything.
Time pillar: microsleep is a duration, PERCLOS is a time-weighted sliding window.
"""
import math
from collections import deque
from dataclasses import dataclass, field

CALIBRATING, OK, UNCERTAIN = "CALIBRATING", "OK", "UNCERTAIN"
LEVEL_OK, LEVEL_WARN, LEVEL_ALARM = 0, 1, 2

# Alert codes; the UI maps them to text.
MICROSLEEP = "MICROSLEEP"
DISTRACTED = "DISTRACTED"
NO_FACE = "NO_FACE"
PERCLOS_HIGH = "PERCLOS_HIGH"
YAWNING = "YAWNING"


@dataclass
class Config:
    calib_seconds: float = 5.0
    close_ratio: float = 0.70     # eye counts as closed below close_ratio * baseline EAR
    open_ratio: float = 0.80      # ...and open again only above open_ratio * baseline (hysteresis)
    blink_max_s: float = 0.5      # closures shorter than this are blinks
    microsleep_s: float = 1.0     # eyes closed this long -> alarm
    perclos_window_s: float = 30.0  # field systems use 60 s; shorter so a demo can show it
    perclos_warn: float = 0.15
    perclos_min_coverage: float = 0.5
    max_gap_s: float = 0.2        # a sample never stands for more than this much time
    yawn_mar: float = 0.55       # mouth counts as open above this (high threshold)
    yawn_mar_close: float = 0.40  # ...and closed again only below this (hysteresis)
    yawn_s: float = 0.5
    yawn_window_s: float = 120.0
    yawn_warn_count: int = 2
    yaw_limit_deg: float = 30.0   # head turned away from the road
    pitch_limit_deg: float = 20.0  # head dropped / raised
    distract_s: float = 2.0
    trust_yaw_deg: float = 25.0   # beyond this the far eye is foreshortened; EAR is not trusted


@dataclass
class Event:
    kind: str
    start: float          # when the condition began (eyes closed / head turned)
    alarm: float          # when the monitor raised it
    end: float = math.nan


@dataclass
class Monitor:
    cfg: Config = field(default_factory=Config)

    def __post_init__(self):
        self.reset()

    def reset(self):
        self.calib = []           # (ear, yaw, pitch) while calibrating
        self.calib_start = None
        self.ear0 = self.yaw0 = self.pitch0 = None
        self.calib_cv = math.nan  # EAR coefficient of variation during calibration
        self.closed = False
        self.closed_since = None
        self.blinks = deque()     # blink end times
        self.perclos_samples = deque()  # (t, dt, closed)
        self.mouth_open_since = None
        self.yawn_counted = False
        self.yawns = deque()
        self.away_since = None
        self.last_t = None
        self.events = []
        self._open = {}           # kind -> Event currently active

    # ---- calibration -----------------------------------------------------
    @property
    def calibrated(self):
        return self.ear0 is not None

    def _calibrate(self, t, obs):
        if obs is None:
            return
        if self.calib_start is None:
            self.calib_start = t
        self.calib.append((obs.ear, obs.yaw, obs.pitch))
        if t - self.calib_start >= self.cfg.calib_seconds and len(self.calib) >= 30:
            ears = sorted(c[0] for c in self.calib)
            # Median, not mean: blinks during calibration should not lower the baseline.
            self.ear0 = _median(ears)
            mean = sum(ears) / len(ears)
            std = math.sqrt(sum((e - mean) ** 2 for e in ears) / len(ears))
            self.calib_cv = std / self.ear0 if self.ear0 > 0 else math.nan
            self.yaw0 = _median([c[1] for c in self.calib if not math.isnan(c[1])] or [0.0])
            self.pitch0 = _median([c[2] for c in self.calib if not math.isnan(c[2])] or [0.0])

    @property
    def close_thr(self):
        return self.cfg.close_ratio * self.ear0 if self.calibrated else math.nan

    @property
    def open_thr(self):
        return self.cfg.open_ratio * self.ear0 if self.calibrated else math.nan

    # ---- events ----------------------------------------------------------
    def _raise(self, kind, start, t):
        if kind not in self._open:
            ev = Event(kind, start, t)
            self._open[kind] = ev
            self.events.append(ev)

    def _clear(self, kind, t):
        ev = self._open.pop(kind, None)
        if ev is not None:
            ev.end = t

    # ---- main update -----------------------------------------------------
    def update(self, t, obs):
        """t: seconds (monotonic). obs: features.Observation or None when no face."""
        dt = 0.0 if self.last_t is None else min(t - self.last_t, self.cfg.max_gap_s)
        self.last_t = t
        if not self.calibrated:
            self._calibrate(t, obs)
            return self._report(t, CALIBRATING, obs, dyaw=math.nan, dpitch=math.nan)

        c = self.cfg
        dyaw = dpitch = math.nan
        trusted = False
        if obs is not None and not math.isnan(obs.yaw):
            dyaw, dpitch = obs.yaw - self.yaw0, obs.pitch - self.pitch0
            trusted = abs(dyaw) <= c.trust_yaw_deg

        # Distraction: face missing or head outside the road cone, sustained.
        away = obs is None or math.isnan(dyaw) or abs(dyaw) > c.yaw_limit_deg or abs(dpitch) > c.pitch_limit_deg
        if away:
            if self.away_since is None:
                self.away_since = t
            if t - self.away_since >= c.distract_s:
                self._raise(NO_FACE if obs is None else DISTRACTED, self.away_since, t)
        else:
            self.away_since = None
            self._clear(NO_FACE, t)
            self._clear(DISTRACTED, t)

        if trusted:
            self._update_eyes(t, dt, obs.ear)
            self._update_mouth(t, obs.mar)
        else:
            # Cannot judge the eyes from here: drop any running closure rather than guess.
            self.closed, self.closed_since = False, None
            self._clear(MICROSLEEP, t)
            self.mouth_open_since = None

        state = OK if trusted else UNCERTAIN
        return self._report(t, state, obs, dyaw, dpitch)

    def _update_eyes(self, t, dt, ear):
        c = self.cfg
        if not self.closed and ear < self.close_thr:
            self.closed, self.closed_since = True, t
        elif self.closed and ear > self.open_thr:
            if t - self.closed_since <= c.blink_max_s:
                self.blinks.append(t)
            self.closed, self.closed_since = False, None
            self._clear(MICROSLEEP, t)
        if self.closed and t - self.closed_since >= c.microsleep_s:
            self._raise(MICROSLEEP, self.closed_since, t)

        self.perclos_samples.append((t, dt, self.closed))
        while self.perclos_samples and self.perclos_samples[0][0] < t - c.perclos_window_s:
            self.perclos_samples.popleft()
        while self.blinks and self.blinks[0] < t - 60.0:
            self.blinks.popleft()

    def _update_mouth(self, t, mar):
        c = self.cfg
        if self.mouth_open_since is None:
            # Mouth closed: open only above the high threshold, so talking
            # (MAR ~0.5) does not start the timer.
            if mar > c.yawn_mar:
                self.mouth_open_since, self.yawn_counted = t, False
        else:
            # Mouth open: stay open until below the low threshold. Without this
            # hysteresis a single noisy frame under yawn_mar resets the timer.
            if mar < c.yawn_mar_close:
                self.mouth_open_since = None
            elif not self.yawn_counted and t - self.mouth_open_since >= c.yawn_s:
                self.yawns.append(t)
                self.yawn_counted = True
        while self.yawns and self.yawns[0] < t - c.yawn_window_s:
            self.yawns.popleft()

    def perclos(self):
        """(fraction of window with eyes closed, fraction of window actually observed)."""
        seen = sum(s[1] for s in self.perclos_samples)
        closed = sum(s[1] for s in self.perclos_samples if s[2])
        frac = closed / seen if seen > 0 else math.nan
        return frac, seen / self.cfg.perclos_window_s

    def _report(self, t, state, obs, dyaw, dpitch):
        c = self.cfg
        perclos, coverage = self.perclos()
        if (not math.isnan(perclos) and coverage >= c.perclos_min_coverage
                and perclos > c.perclos_warn):
            self._raise(PERCLOS_HIGH, t, t)
        else:
            self._clear(PERCLOS_HIGH, t)
        if len(self.yawns) >= c.yawn_warn_count:
            self._raise(YAWNING, self.yawns[0], t)
        else:
            self._clear(YAWNING, t)

        alerts = list(self._open)
        if any(a in (MICROSLEEP, DISTRACTED, NO_FACE) for a in alerts):
            level = LEVEL_ALARM
        elif alerts:
            level = LEVEL_WARN
        else:
            level = LEVEL_OK
        calib_left = math.nan
        if not self.calibrated:
            calib_left = c.calib_seconds - (t - self.calib_start) if self.calib_start is not None else c.calib_seconds
        return {
            "t": t, "state": state, "level": level, "alerts": alerts,
            "ear": obs.ear if obs else math.nan, "close_thr": self.close_thr,
            "open_thr": self.open_thr, "closed": self.closed,
            "perclos": perclos, "perclos_coverage": coverage,
            "blinks_per_min": len(self.blinks), "yawns": len(self.yawns),
            "dyaw": dyaw, "dpitch": dpitch, "calib_left": calib_left,
        }


def _median(xs):
    xs = sorted(xs)
    n = len(xs)
    return xs[n // 2] if n % 2 else 0.5 * (xs[n // 2 - 1] + xs[n // 2])
