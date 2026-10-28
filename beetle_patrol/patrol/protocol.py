"""JSON message protocol (v1) shared by the patrol node, GUI, simulator and tools.

Every message travels as the `data` string of a std_msgs/String. This module is the single source
of truth: `build_*` make a message dict, `validate_*` raise ValueError naming the bad field, and
`parse_command` turns the raw text of a command into a validated dict. No ROS imports, so it runs
on the laptop and under the robot's system Python alike.

zones[].n (the discovery number, int >= 1) and the `set_start` command were added for dynamic zones
without a version bump (PROTOCOL_VERSION stays 1); zones[].row/col may be negative.

Topics (see patrol_node.py): status -> /patrol/status, decision -> /patrol/decision,
warning -> /patrol/warning, command -> /patrol/command.
"""
import json
import math

from .priority import TERMS

PROTOCOL_VERSION = 1

MODES = ("idle", "mapping", "patrol", "estop")
GOAL_STATES = ("none", "sent", "active", "cancelling")
SKIP_REASONS = ("cooldown", "recent")

# Commands that carry no extra fields; the two below carry one each.
SIMPLE_COMMANDS = ("start", "pause", "estop", "release", "arm", "disarm",
                   "explore_start", "explore_stop", "record", "stop_record", "set_start")
COMMANDS = SIMPLE_COMMANDS + ("save_map", "set_weights")

ZONE_KEYS = ("id", "n", "row", "col", "cx", "cy", "w", "h", "risk")
HEATMAP_KEYS = ("age_s", "age_norm", "alert")
MOTION_KEYS = ("lidar", "camera", "fused", "ego_moving", "ego_turning")
SCORE_KEYS = ("zone", "total", "distance_m", "raw", "contrib")
WARNING_KEYS = ("v", "t", "t_robot", "x", "y", "zone", "fused", "lidar", "camera", "message")
STATUS_KEYS = ("v", "t", "mode", "armed", "nav_ready", "explore_active", "robot", "goal_zone",
               "goal_state", "weights", "zones", "heatmap", "skipped", "motion", "decision",
               "last_warning", "recording", "bag_dir")
DECISION_KEYS = ("v", "t", "chosen", "explanation", "weights", "scores")


# --- small field checkers (each raises ValueError naming the field) ----------------------------
def _fail(name, problem):
    raise ValueError(f"{name}: {problem}")


def _require(d, keys, name):
    if not isinstance(d, dict):
        _fail(name, f"must be an object, got {type(d).__name__}")
    for key in keys:
        if key not in d:
            _fail(f"{name}.{key}", "missing")


def _number(value, name, low=None, high=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        _fail(name, f"must be a finite number, got {value!r}")
    if low is not None and value < low:
        _fail(name, f"must be >= {low}, got {value}")
    if high is not None and value > high:
        _fail(name, f"must be <= {high}, got {value}")


def _integer(value, name, low=None):
    if isinstance(value, bool) or not isinstance(value, int):
        _fail(name, f"must be an integer, got {value!r}")
    if low is not None and value < low:
        _fail(name, f"must be >= {low}, got {value}")


def _unit(value, name):
    _number(value, name, 0.0, 1.0)


def _string(value, name, allow_none=False):
    if value is None and allow_none:
        return
    if not isinstance(value, str):
        _fail(name, f"must be a string{' or null' if allow_none else ''}, got {value!r}")


def _boolean(value, name, allow_none=False):
    if value is None and allow_none:
        return
    if not isinstance(value, bool):
        _fail(name, f"must be a boolean{' or null' if allow_none else ''}, got {value!r}")


def _one_of(value, choices, name):
    if value not in choices:
        _fail(name, f"must be one of {list(choices)}, got {value!r}")


def _version(d, name):
    if d["v"] != PROTOCOL_VERSION:
        _fail(f"{name}.v", f"unsupported protocol version {d['v']!r}, expected {PROTOCOL_VERSION}")


def _term_dict(d, name, check):
    """A {age, risk?...} dict with exactly the keys that `check` is applied to."""
    _require(d, TERMS, name)
    for term in TERMS:
        check(d[term], f"{name}.{term}")


def _check_weights(w, name):
    """Weights: all four terms, each >= 0, not all zero."""
    _term_dict(w, name, lambda v, n: _number(v, n, 0.0))
    if sum(w[t] for t in TERMS) <= 0:
        _fail(name, "must not be all zero")


# --- weights ------------------------------------------------------------------------------------
def weights_from_priority(weights):
    """patrol.priority.Weights -> normalised {age, risk, distance, alert} dict (sums to 1)."""
    norm = weights.normalised()
    return {t: getattr(norm, t) for t in TERMS}


# --- builders -----------------------------------------------------------------------------------
def build_decision(t, chosen, explanation, weights, scores):
    """`scores`: list of {zone, total, distance_m, raw:{...}, contrib:{...}}, best first."""
    return {"v": PROTOCOL_VERSION, "t": t, "chosen": chosen, "explanation": explanation,
            "weights": dict(weights), "scores": list(scores)}


def build_warning(t, t_robot, x, y, zone, fused, lidar, camera, message):
    """`t` is the laptop clock, `t_robot` the robot message clock; `zone` None if outside all zones."""
    return {"v": PROTOCOL_VERSION, "t": t, "t_robot": t_robot, "x": x, "y": y, "zone": zone,
            "fused": fused, "lidar": lidar, "camera": camera, "message": message}


def build_status(t, mode, armed, nav_ready, explore_active, robot, goal_zone, goal_state, weights,
                 zones, heatmap, skipped, motion, decision, last_warning, recording, bag_dir):
    """See the module docstring / schema in validate_status. `armed` None means unknown."""
    return {"v": PROTOCOL_VERSION, "t": t, "mode": mode, "armed": armed, "nav_ready": nav_ready,
            "explore_active": explore_active, "robot": robot, "goal_zone": goal_zone,
            "goal_state": goal_state, "weights": dict(weights), "zones": list(zones),
            "heatmap": heatmap, "skipped": skipped, "motion": motion, "decision": decision,
            "last_warning": last_warning, "recording": recording, "bag_dir": bag_dir}


def build_command(cmd, name=None, weights=None):
    """Command dict; `name` only for save_map, `weights` only for set_weights. Validated."""
    command = {"cmd": cmd}
    if name is not None:
        command["name"] = name
    if weights is not None:
        command["weights"] = dict(weights)
    validate_command(command)
    return command


# --- validators ---------------------------------------------------------------------------------
def validate_decision(d, name="decision"):
    _require(d, DECISION_KEYS, name)
    _version(d, name)
    _number(d["t"], f"{name}.t")
    _string(d["chosen"], f"{name}.chosen")
    _string(d["explanation"], f"{name}.explanation")
    _check_weights(d["weights"], f"{name}.weights")
    if not isinstance(d["scores"], list):
        _fail(f"{name}.scores", "must be a list")
    for i, s in enumerate(d["scores"]):
        sname = f"{name}.scores[{i}]"
        _require(s, SCORE_KEYS, sname)
        _string(s["zone"], f"{sname}.zone")
        _number(s["total"], f"{sname}.total", 0.0)
        _number(s["distance_m"], f"{sname}.distance_m", 0.0)
        _term_dict(s["raw"], f"{sname}.raw", _unit)
        _term_dict(s["contrib"], f"{sname}.contrib", lambda v, n: _number(v, n, 0.0))


def validate_warning(d, name="warning"):
    _require(d, WARNING_KEYS, name)
    _version(d, name)
    for key in ("t", "t_robot", "x", "y"):
        _number(d[key], f"{name}.{key}")
    _string(d["zone"], f"{name}.zone", allow_none=True)
    for key in ("fused", "lidar", "camera"):
        _unit(d[key], f"{name}.{key}")
    _string(d["message"], f"{name}.message")


def _validate_zone(z, name):
    _require(z, ZONE_KEYS, name)
    _string(z["id"], f"{name}.id")
    for key in ("n", "row", "col"):
        _integer(z[key], f"{name}.{key}", 1 if key == "n" else None)
    for key in ("cx", "cy"):
        _number(z[key], f"{name}.{key}")
    for key in ("w", "h"):
        _number(z[key], f"{name}.{key}", 0.0)
    _unit(z["risk"], f"{name}.risk")


def validate_status(d, name="status"):
    _require(d, STATUS_KEYS, name)
    _version(d, name)
    _number(d["t"], f"{name}.t")
    _one_of(d["mode"], MODES, f"{name}.mode")
    _boolean(d["armed"], f"{name}.armed", allow_none=True)
    for key in ("nav_ready", "explore_active", "recording"):
        _boolean(d[key], f"{name}.{key}")
    if d["robot"] is not None:
        _require(d["robot"], ("x", "y", "yaw"), f"{name}.robot")
        for key in ("x", "y", "yaw"):
            _number(d["robot"][key], f"{name}.robot.{key}")
    _string(d["goal_zone"], f"{name}.goal_zone", allow_none=True)
    _one_of(d["goal_state"], GOAL_STATES, f"{name}.goal_state")
    _check_weights(d["weights"], f"{name}.weights")
    if not isinstance(d["zones"], list):
        _fail(f"{name}.zones", "must be a list")
    for i, z in enumerate(d["zones"]):
        _validate_zone(z, f"{name}.zones[{i}]")
    if not isinstance(d["heatmap"], dict):
        _fail(f"{name}.heatmap", "must be an object")
    for zid, h in d["heatmap"].items():
        hname = f"{name}.heatmap[{zid}]"
        _require(h, HEATMAP_KEYS, hname)
        _number(h["age_s"], f"{hname}.age_s", 0.0)
        _unit(h["age_norm"], f"{hname}.age_norm")
        _unit(h["alert"], f"{hname}.alert")
    if not isinstance(d["skipped"], dict):
        _fail(f"{name}.skipped", "must be an object")
    for zid, reason in d["skipped"].items():
        _one_of(reason, SKIP_REASONS, f"{name}.skipped[{zid}]")
    if d["motion"] is not None:
        m = d["motion"]
        _require(m, MOTION_KEYS, f"{name}.motion")
        for key in ("lidar", "camera", "fused"):
            _unit(m[key], f"{name}.motion.{key}")
        for key in ("ego_moving", "ego_turning"):
            _boolean(m[key], f"{name}.motion.{key}")
    if d["decision"] is not None:
        validate_decision(d["decision"], f"{name}.decision")
    if d["last_warning"] is not None:
        validate_warning(d["last_warning"], f"{name}.last_warning")
    _string(d["bag_dir"], f"{name}.bag_dir", allow_none=True)


def validate_command(d, name="command"):
    _require(d, ("cmd",), name)
    _one_of(d["cmd"], COMMANDS, f"{name}.cmd")
    allowed = {"cmd"}
    if d["cmd"] == "save_map":
        allowed.add("name")
        if "name" in d:
            _string(d["name"], f"{name}.name")
            if not d["name"].strip():
                _fail(f"{name}.name", "must not be empty")
    elif d["cmd"] == "set_weights":
        allowed.add("weights")
        _require(d, ("weights",), name)
        _check_weights(d["weights"], f"{name}.weights")
    for key in d:
        if key not in allowed:
            _fail(f"{name}.{key}", f"not allowed for command {d['cmd']!r}")


def parse_command(text):
    """Raw command text -> validated command dict.

    Accepts a plain word ('start', 'estop', ...) or a JSON object ({"cmd": "save_map", ...}).
    Plain words only work for commands that take no extra fields.
    """
    if not isinstance(text, str):
        raise ValueError(f"command: must be text, got {type(text).__name__}")
    text = text.strip()
    if text.startswith(("{", "[")):
        try:
            command = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"command: invalid JSON ({exc})") from None
    else:
        command = {"cmd": text.lower()}
        if command["cmd"] in ("save_map", "set_weights"):
            raise ValueError(f"command.{'name' if command['cmd'] == 'save_map' else 'weights'}: "
                             f"{command['cmd']!r} needs a JSON object")
    validate_command(command)
    return command


# --- adapter: PatrolEngine -> status ------------------------------------------------------------
def engine_skipped(engine, now):
    """{zone id: 'cooldown'|'recent'} - the zones next_goal() would skip right now.

    Reads engine._cooldown_until (private, but engine.py has no public accessor) and the public
    zonemap / settings, mirroring the skip rule in PatrolEngine.next_goal.
    """
    skipped = {z.id: "recent" for z in engine.zonemap.zones
               if engine.zonemap.age_s(z.id, now) < engine.settings.priority.min_revisit_s}
    for zid, until in engine._cooldown_until.items():
        if until > now:
            skipped[zid] = "cooldown"   # a failed goal outranks "recently visited" as the reason
    return skipped


def _decision_from_engine(status_decision, weights):
    d = status_decision
    return build_decision(d["t"], d["chosen"], d["explanation"], weights, d["scores"])


def status_from_engine(engine, now, extras):
    """Build the v1 status dict from PatrolEngine.status(now) plus node-side `extras`.

    `extras` supplies what the engine does not know; every key is optional (defaults in brackets):
      mode (engine mode, e.g. 'mapping'), armed [None], nav_ready [False], explore_active [False],
      robot [None] ({x,y,yaw}), goal_zone [None], goal_state ['none'], last_warning [None] (a
      warning dict), recording [False], bag_dir [None].
    Taken from the engine's public attributes: zones (engine.zonemap.zones) and weights
    (engine.weights); skipped via engine_skipped().
    """
    base = engine.status(now)
    weights = weights_from_priority(engine.weights)
    decision = base["decision"]
    return build_status(
        t=now,
        mode=extras.get("mode", base["mode"]),
        armed=extras.get("armed"),
        nav_ready=extras.get("nav_ready", False),
        explore_active=extras.get("explore_active", False),
        robot=extras.get("robot"),
        goal_zone=extras.get("goal_zone"),
        goal_state=extras.get("goal_state", "none"),
        weights=weights,
        zones=[{key: getattr(z, key) for key in ZONE_KEYS} for z in engine.zonemap.zones],
        heatmap=base["heatmap"],
        skipped=engine_skipped(engine, now),
        motion=base["motion"],
        decision=None if decision is None else _decision_from_engine(decision, weights),
        last_warning=extras.get("last_warning"),
        recording=extras.get("recording", False),
        bag_dir=extras.get("bag_dir"))
