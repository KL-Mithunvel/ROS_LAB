"""Weighted zone-priority scoring: decides which zone the robot patrols next.

    score = w_age*age_norm + w_risk*risk + w_distance*closeness + w_alert*alert     (weights sum to 1)

  age_norm  time since last visit, 0..1 (1 = fully stale)            - ZoneMap.age_norm
  risk      fixed importance of the zone, 0..1                       - zones.yaml
  closeness 1 - (straight-line distance / farthest zone distance)    - nearer is better
  alert     recent motion alert in the zone, 1 -> 0 as it fades      - ZoneMap.alert_level

`score_zones` returns every zone with the weighted contribution of each term, so the GUI can show
*why* a zone won, not just that it did.
"""
import math
from dataclasses import dataclass, field

from .schema import from_mapping

TERMS = ("age", "risk", "distance", "alert")


@dataclass
class Weights:
    age: float = 0.5
    risk: float = 0.2
    distance: float = 0.2
    alert: float = 0.1

    def __post_init__(self):
        values = [getattr(self, t) for t in TERMS]
        if any(v < 0 for v in values) or sum(values) <= 0:
            raise ValueError("priority weights must be >= 0 and not all zero")

    def normalised(self):
        total = sum(getattr(self, t) for t in TERMS)
        return Weights(**{t: getattr(self, t) / total for t in TERMS})


def weights_from_dict(values):
    """Validate a {age, risk, distance, alert} dict (all four required) and return normalised Weights.

    Raises ValueError naming the problem; used by the set_weights command.
    """
    if not isinstance(values, dict) or set(values) != set(TERMS):
        raise ValueError(f"weights must have exactly the keys {list(TERMS)}, got {values!r}")
    for term, value in values.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"weights.{term} must be a finite number, got {value!r}")
    return Weights(**values).normalised()


@dataclass
class PriorityConfig:
    weights: dict = field(default_factory=dict)
    failed_goal_cooldown_s: float = 60.0
    min_revisit_s: float = 30.0   # a zone visited this recently is never picked (stops loitering)
    # Engine tuning that lives in this section because config.py has no section for it yet:
    replan_min_interval_s: float = 5.0   # an alert may cancel the current goal at most this often
    goal_timeout_s: float = 90.0         # a Nav2 goal in flight longer than this is cancelled and counted failed
    max_scan_jump_m: float = 0.3         # a scan pose further than this from the previous one is dropped
    max_scan_jump_rad: float = 0.5       # ... or turned by more than this (localisation jump)

    def weight_obj(self):
        return from_mapping(Weights, self.weights, "priority.weights")


@dataclass
class ZoneScore:
    zone_id: str
    raw: dict        # term -> 0..1 value before weighting
    contrib: dict    # term -> weight * raw
    total: float
    distance_m: float


def score_zones(zonemap, robot_xy, now, weights):
    """Score every zone, best first (ties broken by zone id so the order is deterministic)."""
    w = weights.normalised()
    rx, ry = robot_xy
    dists = {z.id: math.hypot(z.cx - rx, z.cy - ry) for z in zonemap.zones}
    farthest = max(dists.values(), default=0.0)   # no zones yet (dynamic mode) -> empty result

    scores = []
    for z in zonemap.zones:
        raw = {
            "age": zonemap.age_norm(z.id, now),
            "risk": z.risk,
            "distance": 1.0 - dists[z.id] / farthest if farthest > 0 else 1.0,
            "alert": zonemap.alert_level(z.id, now),
        }
        contrib = {t: getattr(w, t) * raw[t] for t in TERMS}
        scores.append(ZoneScore(z.id, raw, contrib, sum(contrib.values()), dists[z.id]))
    scores.sort(key=lambda s: (-s.total, s.zone_id))
    return scores


def choose_next(scores, exclude=()):
    """Highest-scoring zone not in `exclude` (e.g. zones Nav2 just failed to reach), or None."""
    for s in scores:
        if s.zone_id not in exclude:
            return s
    return None


def alert_outranks_goal(scores, alerted_zone, goal_zone, exclude=()):
    """True if the alerted zone now scores higher than the zone the robot is driving to.

    `scores` is score_zones() output. A zone in `exclude` (cooling down / just visited) never
    outranks. Alerts inside the goal's own zone, or in an unknown zone, never do.
    """
    if alerted_zone is None or goal_zone is None or alerted_zone == goal_zone or alerted_zone in exclude:
        return False
    by_zone = {s.zone_id: s.total for s in scores}
    if alerted_zone not in by_zone or goal_zone not in by_zone:
        return False
    return by_zone[alerted_zone] > by_zone[goal_zone]


def explain(chosen, scores):
    """One plain-English line on why `chosen` won, for the decision panel and the log."""
    others = [s for s in scores if s.zone_id != chosen.zone_id]
    top_term = max(TERMS, key=lambda t: chosen.contrib[t])
    text = (f"{chosen.zone_id} chosen (score {chosen.total:.2f}, {chosen.distance_m:.1f} m away): "
            f"biggest contributor {top_term} ({chosen.contrib[top_term]:.2f})")
    if others:
        runner = max(others, key=lambda s: s.total)
        edge = max(TERMS, key=lambda t: chosen.contrib[t] - runner.contrib[t])
        text += (f"; beat {runner.zone_id} ({runner.total:.2f}) mainly on {edge} "
                 f"({chosen.contrib[edge] - runner.contrib[edge]:+.2f})")
    return text
