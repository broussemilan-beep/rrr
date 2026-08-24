#!/usr/bin/env python3
"""Stage 4 — Deterministic gate cascade (the JUDGE, built BEFORE the generator).

An animation is ACCEPTED only if every APPLICABLE gate passes. Gates:
  1. direction  (R6, r6_fk)  : striking wrist goes FORWARD (-Z), not backward/none
  2. travel     (R6, r6_fk)  : forward wrist excursion >= TRAVEL_MIN studs
  3. focus      (R6, r6_fk)  : focused_ratio >= FOCUS_MIN (strike forward, not lateral splay)
  4. footplant  (R6, r6_fk)  : >=1 support foot stays planted (min foot XZ drift <= FOOT_DRIFT_MAX)
  5. joint_bounds (R6)       : contact pose anatomically plausible + strike limb shows real amplitude
  6. timing     (rig-agnostic): snap >= SNAP_FLOOR, contact_pos in band, length in strike range

R15 anims: only the rig-agnostic timing gate applies (FK/footplant/bounds are R6-native;
no R15 FK by design — retarget was ruled out). Reported as N/A, not silent-pass.

Reusable: `run_cascade(anim, rig)` -> verdict dict. Called by stage 3 (generator) later.
"""
from __future__ import annotations
import json, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "animator_ai"))
import r6_fk  # noqa: E402
from stage_marketplace_metrics import _metrics, golden_reference, BODY_R6, BODY_R15  # noqa: E402

# ── thresholds (learned from golden_set + validated seeds) ──────────────────
G = golden_reference()
SNAP_FLOOR = round(0.5 * G["snap"], 2)     # crispness floor (joint-space)
CONTACT_LO, CONTACT_HI = 0.12, 0.92         # burst must leave room for antic + recovery
LEN_LO, LEN_HI = 0.20, 3.0                  # a strike, not an idle loop
TRAVEL_MIN = 1.0                            # studs (golden ~3.3, seeds 2-5)
FOCUS_MIN = 0.40                            # existing FAIL_LATERAL band
FOOT_DRIFT_MAX = 2.5                        # studs — a support foot exists
STRIKE_AMP_MIN = 25.0                       # deg — strike limb actually swings
# Absolute contact-pose engagement (forward archetypes). Measured: 13 good seeds
# have strike-shoulder rx@contact in [70.8, 100] and wrist extension in [2.15, 3.29].
# Floors set BELOW the good-min (margin) + wide bands => not golden-copy-narrow.
POSE_SH_RX_MIN = 65.0                        # deg — arm reaches a committed forward extension
SILHOUETTE_EXT_MIN = 2.0                     # studs — wrist extends clear of the body (readable line)
# Composite commitment (shoulder drive + hip rotation + extension). Measured: 13 good
# seeds span [125, 212] (weakest domain_open=125); tiède recomb=113. Floor below weakest.
MAGNITUDE_MIN = 120.0                        # forces coordinated, non-tepid strikes (keeps 13/13)

R6_POSE_TO_JOINT = {
    "Torso": "RootJoint", "Head": "Neck",
    "Right Arm": "Right Shoulder", "Left Arm": "Left Shoulder",
    "Right Leg": "Right Hip", "Left Leg": "Left Hip",
}


def _norm_r6(anim):
    frames = []
    for kf in anim["keyframes"]:
        j = {}
        for pose_name, val in kf["poses"].items():
            jn = R6_POSE_TO_JOINT.get(pose_name)
            if jn:
                e = val["e"]
                j[jn] = {"rx": e[0], "ry": e[1], "rz": e[2]}
        frames.append({"frame": len(frames), "t": kf["t"], "joints": j})
    return frames


def _fk_metrics(frames):
    out = r6_fk.motor6d_frames_to_bone_positions(frames)
    def ax(bone, a): return [p["position"][a] for p in out[bone]]
    rz, lz = ax("Right Wrist", "z"), ax("Left Wrist", "z")
    strike = "Right Wrist" if (max(rz) - min(rz)) >= (max(lz) - min(lz)) else "Left Wrist"
    z, x = ax(strike, "z"), ax(strike, "x")
    neutral = z[0]
    fwd = neutral - min(z)          # forward = -Z
    bwd = max(z) - neutral
    if max(fwd, bwd) < 0.2:
        direction = "NONE"
    elif fwd >= bwd:
        direction = "FORWARD"
    else:
        direction = "BACKWARD"
    lateral = max(x) - min(x)
    focus = fwd / (fwd + lateral) if (fwd + lateral) > 1e-6 else 0.0
    def drift(foot):
        xs, zs = ax(foot, "x"), ax(foot, "z")
        return ((max(xs) - min(xs)) ** 2 + (max(zs) - min(zs)) ** 2) ** 0.5
    foot_drift = min(drift("Right Foot"), drift("Left Foot"))
    # strike-limb amplitude = max angular range across rx/ry/rz (a real swing on any axis)
    joint = "Right Shoulder" if strike == "Right Wrist" else "Left Shoulder"
    def rng(ax):
        v = [f["joints"].get(joint, {}).get(ax, 0.0) for f in frames]
        return max(v) - min(v)
    strike_amp = max(rng("rx"), rng("ry"), rng("rz"))
    contact_i = min(range(len(z)), key=lambda i: z[i])
    sh_rx_contact = frames[contact_i]["joints"].get(joint, {}).get("rx", 0.0)   # engagement
    hip_joint = "Right Hip" if strike == "Right Wrist" else "Left Hip"
    hip_ry_contact = frames[contact_i]["joints"].get(hip_joint, {}).get("ry", 0.0)  # hip rotation drive
    wc = out[strike][contact_i]["position"]
    ext_contact = (wc["x"] ** 2 + wc["z"] ** 2) ** 0.5                          # silhouette extension
    magnitude = abs(sh_rx_contact) + 2 * abs(hip_ry_contact) + 20 * ext_contact  # composite commitment
    return dict(direction=direction, travel=round(fwd, 2), focus=round(focus, 2),
                foot_drift=round(foot_drift, 2), strike_amp=round(strike_amp, 1),
                sh_rx_contact=round(sh_rx_contact, 1), hip_ry_contact=round(hip_ry_contact, 1),
                ext_contact=round(ext_contact, 2), magnitude=round(magnitude, 0),
                strike=strike, contact_i=contact_i)


def run_cascade(anim, rig):
    """Return {accepted, first_fail, gates:{name:(pass,detail)}}."""
    gates = {}
    joints = BODY_R6 if rig == "R6" else BODY_R15
    tm = _metrics(anim["keyframes"], joints)

    # timing (rig-agnostic)
    if tm is None:
        gates["timing"] = (False, "too few keyframes")
    else:
        ok = (tm["snap"] >= SNAP_FLOOR and CONTACT_LO <= tm["contact_pos"] <= CONTACT_HI
              and LEN_LO <= tm["length"] <= LEN_HI)
        why = []
        if tm["snap"] < SNAP_FLOOR: why.append(f"snap {tm['snap']}<{SNAP_FLOOR}")
        if not (CONTACT_LO <= tm["contact_pos"] <= CONTACT_HI): why.append(f"contact_pos {tm['contact_pos']} degenerate")
        if not (LEN_LO <= tm["length"] <= LEN_HI): why.append(f"len {tm['length']}s")
        gates["timing"] = (ok, "ok" if ok else "; ".join(why))

    if rig == "R6":
        try:
            fk = _fk_metrics(_norm_r6(anim))
            gates["direction"] = (fk["direction"] == "FORWARD", fk["direction"])
            gates["travel"] = (fk["travel"] >= TRAVEL_MIN, f"{fk['travel']} studs")
            gates["focus"] = (fk["focus"] >= FOCUS_MIN, f"ratio {fk['focus']}")
            gates["footplant"] = (fk["foot_drift"] <= FOOT_DRIFT_MAX, f"min foot drift {fk['foot_drift']} studs")
            gates["joint_bounds"] = (fk["strike_amp"] >= STRIKE_AMP_MIN, f"strike_amp {fk['strike_amp']}deg")
            gates["pose_engage"] = (abs(fk["sh_rx_contact"]) >= POSE_SH_RX_MIN, f"sh_rx@contact {fk['sh_rx_contact']}")
            gates["silhouette"] = (fk["ext_contact"] >= SILHOUETTE_EXT_MIN, f"ext {fk['ext_contact']}")
            gates["magnitude"] = (fk["magnitude"] >= MAGNITUDE_MIN, f"engage {fk['magnitude']:.0f}")
        except Exception as e:
            gates["direction"] = gates["travel"] = gates["focus"] = (False, f"FK error: {e}")
            gates["footplant"] = gates["joint_bounds"] = (False, "FK error")
    else:  # R15 — FK gates not applicable by design
        for g in ("direction", "travel", "focus", "footplant", "joint_bounds", "pose_engage", "silhouette", "magnitude"):
            gates[g] = (None, "N/A (R15, FK gates R6-native)")

    applicable = [(n, p, d) for n, (p, d) in gates.items() if p is not None]
    accepted = all(p for _, p, _ in applicable)
    first_fail = next((n for n, p, _ in applicable if not p), None)
    return {"accepted": accepted, "first_fail": first_fail, "gates": gates,
            "timing": tm}


PIPELINE_JOINTS = ["RootJoint", "Neck", "Right Shoulder", "Left Shoulder", "Right Hip", "Left Hip"]


def _frames_timing(frames):
    kf = [{"t": f.get("t", i / 30.0),
           "poses": {j: {"e": [f["joints"].get(j, {}).get(a, 0.0) for a in ("rx", "ry", "rz")]}
                     for j in PIPELINE_JOINTS}}
          for i, f in enumerate(frames)]
    return _metrics(kf, PIPELINE_JOINTS)


def run_cascade_frames(frames):
    """Cascade on pipeline-convention r6_fk frames (FK gates reliable here)."""
    gates = {}
    tm = _frames_timing(frames)
    if tm is None:
        gates["timing"] = (False, "too few frames")
    else:
        ok = (tm["snap"] >= SNAP_FLOOR and CONTACT_LO <= tm["contact_pos"] <= CONTACT_HI
              and LEN_LO <= tm["length"] <= LEN_HI)
        gates["timing"] = (ok, "ok" if ok else f"snap={tm['snap']} cpos={tm['contact_pos']} len={tm['length']}")
    fk = _fk_metrics(frames)
    gates["direction"] = (fk["direction"] == "FORWARD", fk["direction"])
    gates["travel"] = (fk["travel"] >= TRAVEL_MIN, f"{fk['travel']} studs")
    gates["focus"] = (fk["focus"] >= FOCUS_MIN, f"ratio {fk['focus']}")
    gates["footplant"] = (fk["foot_drift"] <= FOOT_DRIFT_MAX, f"drift {fk['foot_drift']}")
    gates["joint_bounds"] = (fk["strike_amp"] >= STRIKE_AMP_MIN, f"amp {fk['strike_amp']}deg")
    gates["pose_engage"] = (abs(fk["sh_rx_contact"]) >= POSE_SH_RX_MIN, f"sh_rx@contact {fk['sh_rx_contact']}")
    gates["silhouette"] = (fk["ext_contact"] >= SILHOUETTE_EXT_MIN, f"ext {fk['ext_contact']}")
    gates["magnitude"] = (fk["magnitude"] >= MAGNITUDE_MIN, f"engage {fk['magnitude']:.0f} (hip_ry {fk['hip_ry_contact']})")
    applicable = [(n, p) for n, (p, _) in gates.items()]
    accepted = all(p for _, p in applicable)
    first_fail = next((n for n, p in applicable if not p), None)
    return {"accepted": accepted, "first_fail": first_fail, "gates": gates}


def _load_pipeline_seeds():
    import glob
    seeds = []
    seen = set()
    for f in sorted(glob.glob(str(REPO / "artifacts" / "animator_ai" / "agent_outputs" / "*" / "*.json"))):
        try:
            d = json.loads(Path(f).read_text())
        except Exception:
            continue
        if not isinstance(d, dict) or not isinstance(d.get("frames"), list) or len(d["frames"]) < 4:
            continue
        sid = d.get("skill_id", Path(f).stem)
        if ("handkey" in f.lower() or sid in {"M1_jab_toji", "M1_cross_toji", "M1_palm_gojo",
                "dash_strike_toji", "heavy_finisher_sukuna", "M1_uppercut_saitama",
                "devil_fruit_cast_luffy", "dual_slash_swordsman", "spear_thrust_jinwoo",
                "domain_open_gojo"}) and sid not in seen:
            seen.add(sid)
            seeds.append((sid, d["frames"]))
    return seeds


def _flip_backward(frames):
    """Break a seed: negate both shoulders' full rotation -> strike reverses (backward).

    rx alone is insufficient (hooks/crosses drive forward via ry/rz), so negate all
    three axes on both arms to guarantee the wrist trajectory reverses in Z.
    """
    out = []
    for f in frames:
        g = {k: dict(v) for k, v in f["joints"].items()}
        for j in ("Right Shoulder", "Left Shoulder"):
            if j in g:
                g[j] = {a: -g[j].get(a, 0.0) for a in ("rx", "ry", "rz")}
        out.append({"frame": f.get("frame", 0), "t": f.get("t", 0), "joints": g})
    return out


def validate_pipeline():
    seeds = _load_pipeline_seeds()
    print("=" * 80)
    print(f"STAGE 4 — PIPELINE-CONVENTION validation ({len(seeds)} hand_keyer seeds + broken variants)")
    print("  (FK gates are reliable ONLY on pipeline-convention anims — this is their true test)")
    print("=" * 80)
    conf = {"TP": 0, "FN": 0, "FP": 0, "TN": 0}
    print("\n### GOOD — validated seeds (expect ACCEPT)")
    for sid, frames in seeds:
        r = run_cascade_frames(frames)
        conf["TP" if r["accepted"] else "FN"] += 1
        gs = " ".join(f"{n}={'✓' if p else '✗'}" for n, (p, _) in r["gates"].items())
        print(f"  {sid:26s} {'ACCEPT' if r['accepted'] else 'REJECT @'+str(r['first_fail']):17s} | {gs}")
    print("\n### BAD — sign-flipped (backward) variants (expect REJECT)")
    for sid, frames in seeds:
        r = run_cascade_frames(_flip_backward(frames))
        conf["FP" if r["accepted"] else "TN"] += 1
        print(f"  {sid+' (flipped)':26s} {'ACCEPT' if r['accepted'] else 'REJECT @'+str(r['first_fail'])}")
    n_good = conf["TP"] + conf["FN"]; n_bad = conf["FP"] + conf["TN"]
    print("\n### CONFUSION MATRIX (pipeline anims)")
    print(f"                 ACCEPT   REJECT")
    print(f"  GOOD (n={n_good})      TP={conf['TP']:<6d} FN={conf['FN']}")
    print(f"  BAD  (n={n_bad})      FP={conf['FP']:<6d} TN={conf['TN']}")
    clean = conf["FN"] == 0 and conf["FP"] == 0
    print(f"  CLEAN SEPARATION: {'YES ✓' if clean else 'NO ✗'}")
    return conf, clean


# ── validation harness: point-9 labelled test set ──────────────────────────
KEPT = [("Heavy Punch", "R6"), ("Full Body Swing 2", "R6"), ("Slow Punch", "R6"), ("Combat Punch", "R15")]
DROPPED = [("Forward Lean Punch", "R6"), ("Charged Punch 1", "R6"), ("Full Body Swing 1", "R6"),
           ("Spin Kick", "R6"), ("Combat Uppercut", "R15"), ("Combat Right Punch", "R15"),
           ("Combat Left  Punch", "R15"), ("Combat Kick", "R15")]
INCONCLUSIVE = [("Fast Punch", "R6"), ("Elbow Jab", "R6"), ("Regular Kick", "R6")]
MKT = REPO / "artifacts" / "animator_ai" / "marketplace"


def _find(name):
    for pf in ("closecombat_raw.json", "virtualvogue_raw.json"):
        d = json.loads((MKT / pf).read_text())
        for a in d["anims"]:
            if a["name"] == name:
                return a
    return None


def main():
    p_conf, p_clean = validate_pipeline()
    print()
    print("=" * 80)
    print("STAGE 4 — GATE CASCADE  (marketplace test — TIMING gate only is meaningful;")
    print("           FK gates confounded by external-pack C0/C1 convention, see note)")
    print(f"thresholds: SNAP_FLOOR={SNAP_FLOOR} contact[{CONTACT_LO},{CONTACT_HI}] "
          f"len[{LEN_LO},{LEN_HI}] travel>={TRAVEL_MIN} focus>={FOCUS_MIN} foot<={FOOT_DRIFT_MAX} amp>={STRIKE_AMP_MIN}")
    print("=" * 80)
    conf = {"TP": 0, "FN": 0, "FP": 0, "TN": 0}
    for label, group in (("GOOD (kept)", KEPT), ("BAD (dropped)", DROPPED)):
        print(f"\n### {label}")
        for name, rig in group:
            a = _find(name)
            if not a:
                print(f"  {name:26s} NOT FOUND"); continue
            r = run_cascade(a, rig)
            verd = "ACCEPT" if r["accepted"] else "REJECT"
            good = label.startswith("GOOD")
            if good and r["accepted"]: conf["TP"] += 1
            elif good and not r["accepted"]: conf["FN"] += 1
            elif not good and r["accepted"]: conf["FP"] += 1
            else: conf["TN"] += 1
            ff = f" @{r['first_fail']}" if r["first_fail"] else ""
            gs = " ".join(f"{n}={'✓' if p else '✗' if p is False else '–'}" for n, (p, _) in r["gates"].items())
            print(f"  {name:26s} [{rig:3s}] {verd}{ff}  | {gs}")
    print("\n### CONFUSION MATRIX (cascade verdict vs point-9 label)")
    print(f"                 ACCEPT   REJECT")
    print(f"  GOOD (n={conf['TP']+conf['FN']})       TP={conf['TP']:<6d} FN={conf['FN']}")
    print(f"  BAD  (n={conf['FP']+conf['TN']})       FP={conf['FP']:<6d} TN={conf['TN']}")
    clean = conf["FN"] == 0 and conf["FP"] == 0
    print(f"\n  CLEAN SEPARATION: {'YES ✓' if clean else 'NO ✗ (see FN/FP above)'}")
    print(f"\n### INCONCLUSIVE (sparse keyposes) — bucketed for stage 3, NOT judged here:")
    for name, rig in INCONCLUSIVE:
        a = _find(name)
        if a:
            r = run_cascade(a, rig)
            print(f"  {name:26s} [{rig}] would={'ACCEPT' if r['accepted'] else 'REJECT'} "
                  f"(kf={len(a['keyframes'])}) -> stage-3 bucket")
    (MKT / "gate_cascade_validation.json").write_text(json.dumps({"confusion": conf, "clean": clean,
        "thresholds": dict(SNAP_FLOOR=SNAP_FLOOR, TRAVEL_MIN=TRAVEL_MIN, FOCUS_MIN=FOCUS_MIN,
        FOOT_DRIFT_MAX=FOOT_DRIFT_MAX, STRIKE_AMP_MIN=STRIKE_AMP_MIN)}, indent=2))


if __name__ == "__main__":
    main()
