"""r6_fk.py — pure-math forward kinematics for R6 Motor6D animations.

Computes bone WORLD POSITIONS (relative to HumanoidRootPart) from a sequence
of Motor6D rotation frames, using the exact Roblox CFrame composition:

    BoneWorld = ParentWorld * C0 * Transform * C1^-1

with Transform = CFrame.Angles(rx, ry, rz) interpreted as Roblox
ToEulerAnglesXYZ (intrinsic X-Y-Z). Roblox convention: Y-up, -Z forward,
+X right, units = studs.

Output shape matches ``artifacts/golden_set/<class>/reference_data.json``
``bone_positions`` so the result feeds directly into
``scripts/agent_orchestration/rmse_comparator.compute_rmse_per_bone``.

The R6 part dimensions + Motor6D C0/C1 used here are the engine-canonical
values (not the Blender debug-rig values), because we score against
ground-truth positions extracted via Studio MCP from the running engine.

Public surface:
    motor6d_frames_to_bone_positions(frames: list[dict]) → dict[bone → list[{t, position}]]
    pose_to_bone_positions(joints: dict) → dict[bone → {x, y, z}]   (single pose)
"""

from __future__ import annotations

import math
import numpy as np


# ─── R6 engine-canonical part dimensions (studs) ──────────────────────────
# Source: Roblox classic R6 rig. Each part is a rectangular block with center
# at the part's CFrame.Position.
TORSO_DIMS = (2.0, 2.0, 1.0)
HEAD_DIMS = (2.0, 1.0, 1.0)
ARM_DIMS = (1.0, 2.0, 1.0)
LEG_DIMS = (1.0, 2.0, 1.0)


# ─── Motor6D C0 / C1 attachments (engine-canonical, WITH rotation) ─────────
# C0 = attachment on the PARENT part (in parent-local frame).
# C1 = attachment on the CHILD  part (in child-local frame).
#
# Every R6 Motor6D carries a ROTATION in C0/C1, not just a translation. The
# values below were read straight off a live R6 rig via Studio MCP on
# 2026-08-24 (`Motor6D.C0:GetComponents()`), not reconstructed from memory.
#
# Because C0 and C1 carry the SAME rotation on every joint, they cancel at
# rest (``C0 · C1⁻¹`` is a pure translation) — which is why modelling them as
# translations gave the correct NEUTRAL pose and the error stayed invisible.
# They do NOT cancel once ``Transform`` is non-identity: the engine evaluates
# ``C0 · Transform · C1⁻¹``, so the rotation happens in the C0-rotated frame.
#
# Concretely, for "Right Shoulder" the C0 rotation maps the joint's local X
# onto the torso's −Z. A CFrame.Angles(rx, 0, 0) is therefore a CORONAL
# (lateral / cross-body) sweep in the engine, not a sagittal punch — the
# forward swing lives on ``rz``. Modelling C0 as identity silently swapped the
# sagittal and coronal planes; measured on M1_jab_toji it turned a 0.19-stud
# forward travel into a reported 3.04.
_ROT_ROOT = np.array([[-1.0, 0.0, 0.0],
                        [0.0, 0.0, 1.0],
                        [0.0, 1.0, 0.0]])          # RootJoint + Neck
_ROT_RIGHT = np.array([[0.0, 0.0, 1.0],
                         [0.0, 1.0, 0.0],
                         [-1.0, 0.0, 0.0]])         # Right Shoulder + Right Hip
_ROT_LEFT = np.array([[0.0, 0.0, -1.0],
                        [0.0, 1.0, 0.0],
                        [1.0, 0.0, 0.0]])           # Left Shoulder + Left Hip

_MOTORS: dict[str, dict] = {
    # HumanoidRootPart → Torso  (root has no offset; characters can spawn
    # at any Y but the rig itself is identity-rooted).
    "RootJoint":      {"parent": "HumanoidRootPart", "child": "Torso",
                         "c0": (0.0, 0.0, 0.0), "c1": (0.0, 0.0, 0.0),
                         "rot": _ROT_ROOT},
    # Torso → Head — neck attachment 1 stud above Torso centre, 0.5 below Head.
    "Neck":           {"parent": "Torso", "child": "Head",
                         "c0": (0.0, +1.0, 0.0), "c1": (0.0, -0.5, 0.0),
                         "rot": _ROT_ROOT},
    # Torso → Right Arm
    "Right Shoulder": {"parent": "Torso", "child": "Right Arm",
                         "c0": (+1.0, +0.5, 0.0), "c1": (-0.5, +0.5, 0.0),
                         "rot": _ROT_RIGHT},
    # Torso → Left Arm  (mirrored)
    "Left Shoulder":  {"parent": "Torso", "child": "Left Arm",
                         "c0": (-1.0, +0.5, 0.0), "c1": (+0.5, +0.5, 0.0),
                         "rot": _ROT_LEFT},
    # Torso → Right Leg. NOTE the C0/C1 translations differ from the pre-fix
    # values (+0.5,-1,0)/(0,+1,0): those had the same DIFFERENCE, so the rest
    # pose matched, but the split is what the engine actually uses once the
    # joint rotates.
    "Right Hip":      {"parent": "Torso", "child": "Right Leg",
                         "c0": (+1.0, -1.0, 0.0), "c1": (+0.5, +1.0, 0.0),
                         "rot": _ROT_RIGHT},
    # Torso → Left Leg
    "Left Hip":       {"parent": "Torso", "child": "Left Leg",
                         "c0": (-1.0, -1.0, 0.0), "c1": (-0.5, +1.0, 0.0),
                         "rot": _ROT_LEFT},
}


def _cframe_angles_xyz(rx_deg: float, ry_deg: float, rz_deg: float) -> np.ndarray:
    """Roblox CFrame.Angles(rx,ry,rz) → 3×3 rotation matrix.

    Roblox CFrame.Angles uses extrinsic X-Y-Z order: R = Rx · Ry · Rz, applied
    to column vectors. This is the inverse decomposition of
    ``CFrame:ToEulerAnglesXYZ``, the function used by
    ``animation_runtime_extractor`` to populate ``yuji_bfp.motor6d_trajectories``.
    """
    rx = math.radians(rx_deg)
    ry = math.radians(ry_deg)
    rz = math.radians(rz_deg)
    cx, sx = math.cos(rx), math.sin(rx)
    cy, sy = math.cos(ry), math.sin(ry)
    cz, sz = math.cos(rz), math.sin(rz)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return Rx @ Ry @ Rz


def _make_cframe(rot: np.ndarray, pos: np.ndarray) -> np.ndarray:
    """Build a 4×4 homogeneous CFrame from 3×3 rotation + 3-vector translation."""
    M = np.eye(4)
    M[:3, :3] = rot
    M[:3, 3] = pos
    return M


def _translation(t: tuple[float, float, float]) -> np.ndarray:
    return _make_cframe(np.eye(3), np.array(t))


def _attachment(motor: dict, which: str) -> np.ndarray:
    """Build the engine C0 or C1 CFrame for ``motor`` (translation + rotation)."""
    return _make_cframe(motor["rot"], np.array(motor[which]))


def _inverse(M: np.ndarray) -> np.ndarray:
    """Inverse of a rigid (rotation + translation) 4×4 matrix."""
    R = M[:3, :3]
    t = M[:3, 3]
    out = np.eye(4)
    out[:3, :3] = R.T
    out[:3, 3] = -R.T @ t
    return out


# Effector tip offset in each child's local frame (relative to part center).
# Arms/legs are 2-tall along their local Y; tip = center + (0, -1, 0) so the
# wrist/foot sits at the bottom of the part. Head's effector is its top.
_EFFECTOR_TIPS: dict[str, np.ndarray] = {
    "Right Arm": np.array([0.0, -1.0, 0.0]),
    "Left Arm":  np.array([0.0, -1.0, 0.0]),
    "Right Leg": np.array([0.0, -1.0, 0.0]),
    "Left Leg":  np.array([0.0, -1.0, 0.0]),
    "Head":      np.array([0.0, +0.5, 0.0]),
}


def pose_to_bone_positions(joints: dict,
                            root_translation: dict | None = None) -> dict[str, dict]:
    """Compute one frame's bone+effector world positions from one pose dict.

    Returns ``{name: {"x", "y", "z"}}`` for the 7 R6 bones (centres) AND the
    five effector tips (Right Wrist, Left Wrist, Right Foot, Left Foot, Head
    Top) — the effector tips are critical because the arm's CENTRE barely
    moves when the arm twists around its own long axis (rotation that does
    NOT translate the centre), whereas the wrist tip swings widely. Without
    the tip, a "punch backward" and "arm at side" can score similarly on
    centre-only RMSE.

    HumanoidRootPart is at origin (0,0,0) by default; positions are in
    torso-local (= HRP) frame so they can be RMSE-compared against any
    ``reference_data.bone_positions`` that has been mean-centred on HRP.

    ``root_translation`` (v2): when provided as ``{"x":, "y":, "z":}``, the
    HRP is shifted by that vector and ALL bone positions are translated
    accordingly. v1 callers (None) get the identical legacy behavior. The
    critic's RMSE path is unaffected because it subtracts HRP before
    comparison (per-bone offsets relative to HRP are unchanged).
    """
    def _eul(name: str) -> tuple[float, float, float]:
        j = joints.get(name) or {}
        return (
            float(j.get("rx", 0.0)),
            float(j.get("ry", 0.0)),
            float(j.get("rz", 0.0)),
        )

    # HumanoidRootPart at origin (v1) or at root_translation (v2).
    rt_dx = rt_dy = rt_dz = 0.0
    if root_translation is not None:
        rt_dx = float(root_translation.get("x", 0.0))
        rt_dy = float(root_translation.get("y", 0.0))
        rt_dz = float(root_translation.get("z", 0.0))
    hrp_cf = np.eye(4)
    hrp_cf[0, 3] = rt_dx
    hrp_cf[1, 3] = rt_dy
    hrp_cf[2, 3] = rt_dz

    # Torso = HRP · C0_root · Transform_root · C1_root^-1
    m = _MOTORS["RootJoint"]
    root_cf = (hrp_cf
                 @ _attachment(m, "c0")
                 @ _make_cframe(_cframe_angles_xyz(*_eul("RootJoint")),
                                  np.zeros(3))
                 @ _inverse(_attachment(m, "c1")))
    torso_cf = root_cf  # naming for clarity downstream

    bones: dict[str, dict] = {}
    bones["HumanoidRootPart"] = {"x": rt_dx, "y": rt_dy, "z": rt_dz}
    bones["Torso"] = {
        "x": float(torso_cf[0, 3]),
        "y": float(torso_cf[1, 3]),
        "z": float(torso_cf[2, 3]),
    }

    # Effector-tip name per child (the rotation-sensitive sample point).
    _EFFECTOR_NAMES = {
        "Head":      "Head Top",
        "Right Arm": "Right Wrist",
        "Left Arm":  "Left Wrist",
        "Right Leg": "Right Foot",
        "Left Leg":  "Left Foot",
    }

    # Each child = Torso · C0 · Transform · C1^-1
    children = [
        ("Neck",           "Head"),
        ("Right Shoulder", "Right Arm"),
        ("Left Shoulder",  "Left Arm"),
        ("Right Hip",      "Right Leg"),
        ("Left Hip",       "Left Leg"),
    ]
    for motor, child in children:
        m = _MOTORS[motor]
        child_cf = (torso_cf
                      @ _attachment(m, "c0")
                      @ _make_cframe(_cframe_angles_xyz(*_eul(motor)),
                                       np.zeros(3))
                      @ _inverse(_attachment(m, "c1")))
        bones[child] = {
            "x": float(child_cf[0, 3]),
            "y": float(child_cf[1, 3]),
            "z": float(child_cf[2, 3]),
        }
        # Effector tip = child_cf · local_tip (homogeneous transform)
        tip_local = _EFFECTOR_TIPS[child]
        tip_world = child_cf[:3, :3] @ tip_local + child_cf[:3, 3]
        bones[_EFFECTOR_NAMES[child]] = {
            "x": float(tip_world[0]),
            "y": float(tip_world[1]),
            "z": float(tip_world[2]),
        }
    return bones


def motor6d_frames_to_bone_positions(frames: list[dict]) -> dict[str, list[dict]]:
    """Apply ``pose_to_bone_positions`` per frame.

    Input  : list of ``{frame, t, joints: {<motor>: {rx, ry, rz}}, ...}`` —
             the schema produced by the animator agent / motion_to_r6.py / ik_retarget.
    Output : ``{bone: [{t, position: {x,y,z}}, ...]}`` for the 7 R6 bones —
             matches ``reference_data.bone_positions`` so it slots into
             ``rmse_comparator.compute_rmse_per_bone`` with no adapter.
    """
    bone_traj: dict[str, list[dict]] = {b: [] for b in (
        "HumanoidRootPart", "Torso", "Head",
        "Right Arm", "Left Arm", "Right Leg", "Left Leg",
        # Effector tips — see pose_to_bone_positions docstring.
        "Head Top", "Right Wrist", "Left Wrist", "Right Foot", "Left Foot",
    )}
    for f in frames:
        t = float(f.get("t", 0.0))
        # v2: pick up per-frame root_translation if present. v1 frames have no
        # field → root_translation defaults to None → identical legacy behavior.
        positions = pose_to_bone_positions(
            f.get("joints") or {},
            root_translation=f.get("root_translation"),
        )
        for bone, pos in positions.items():
            bone_traj[bone].append({"t": t, "position": pos})
    return bone_traj
