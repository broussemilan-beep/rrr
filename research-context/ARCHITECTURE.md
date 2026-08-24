# Animation architecture — current state

Summary of the animation stack a Roblox R6 combat game is built on. Written for
external researchers; the game source is not in this repository.

## Rig: R6, not R15

Six body parts (Torso, Head, Right/Left Arm, Right/Left Leg) plus a
HumanoidRootPart, connected by six `Motor6D` joints:

```
HumanoidRootPart --RootJoint--> Torso
Torso --Neck--------------> Head
Torso --Right Shoulder----> Right Arm
Torso --Left Shoulder-----> Left Arm
Torso --Right Hip---------> Right Leg
Torso --Left Hip----------> Left Leg
```

Every joint has exactly 3 rotational DOF and no translation, so a pose is 18
numbers. Animations are authored directly in this space (a per-frame dict of
`{joint: {rx, ry, rz}}` in degrees) and baked into a `KeyframeSequence`.

R15 (15 parts) was ruled out: retargeting was evaluated and dropped, so the
FK-based gates below are R6-native and report `N/A` on R15 input rather than
silently passing it.

Roblox conventions used throughout: Y up, **−Z forward**, +X right, units in
studs (1 stud ≈ 0.28 m at default character scale).

## Gate cascade — the deterministic judge

An animation is accepted only if every applicable gate passes. The cascade was
built *before* the generator, deliberately, so the generator could never be
tuned against a moving target.

| gate | rig | criterion |
|---|---|---|
| `direction` | R6 (FK) | striking wrist travels FORWARD (−Z), not backward or nowhere |
| `travel` | R6 (FK) | forward wrist excursion ≥ 1.0 stud |
| `focus` | R6 (FK) | `focused_ratio = forward / (forward + lateral)` ≥ 0.40 — a strike, not a lateral splay |
| `footplant` | R6 (FK) | at least one support foot stays planted (min foot XZ drift ≤ 2.5 studs) |
| `joint_bounds` | R6 | strike limb shows a real swing (≥ 25° range on some axis) |
| `pose_engage` | R6 | shoulder rx at contact ≥ 65° — a committed forward extension |
| `silhouette` | R6 | wrist extends ≥ 2.0 studs clear of the body (readable line at a standstill) |
| `magnitude` | R6 | composite commitment `\|sh_rx\| + 2·\|hip_ry\| + 20·ext` ≥ 120 — no tepid strikes |
| `timing` | rig-agnostic | snap ≥ floor, contact position in [0.12, 0.92] of length, length in [0.20, 3.0] s |

Thresholds were set below the weakest known-good sample, not at its mean, so the
cascade is not a golden-copy detector.

**Validation: 13/13 intended-good animations accepted (no false negatives), 8/8
mediocre marketplace animations rejected (no false positives).** The mediocre set
is rejected by the `timing` gate. Degenerate variants (soft/mushy, drifting) were
also rejected 6/6.

## Two measurement bugs found and fixed

Both had the same shape: the geometric judge was internally consistent and wrong,
and only an external signal — positions measured inside the running engine — exposed it.

### 1. `r6_fk.py` treated `Motor6D` C0/C1 as pure translations

Forward kinematics composes `BoneWorld = ParentWorld · C0 · Transform · C1⁻¹`.
The implementation modelled every `C0`/`C1` attachment as a translation with
identity rotation. Read off a live rig, they carry real rotations:

```
RootJoint / Neck            C0rot = C1rot = (-90,   0, -180)
Right Shoulder / Right Hip  C0rot = C1rot = (  0, +90,    0)
Left Shoulder  / Left Hip   C0rot = C1rot = (  0, -90,    0)
```

Because `C0rot == C1rot` on every joint, they cancel at rest — `C0 · C1⁻¹` is a
pure translation — so the **neutral pose was correct** and the bug stayed
invisible for months. They stop cancelling the moment `Transform ≠ identity`.

For the shoulders, the C0 rotation maps the joint's local X axis onto the torso's
∓Z. So `rx` — which the whole authoring pipeline treated as the **sagittal**
(forward punch) swing — is a **coronal**, cross-body sweep in the engine. The
forward swing actually lives on `rz` (positive on the right side, negative on the
left). The FK had the sagittal and coronal planes swapped.

A second defect hid in the same table: the hips' C0/C1 translations were
`(+0.5,−1,0)` / `(0,+1,0)` instead of the engine's `(+1,−1,0)` / `(+0.5,+1,0)`.
Same *difference*, hence the correct rest pose again, but the split is what the
engine uses once the joint rotates.

Measured impact on one seed the gate had passed as a clean forward jab: the gate
reported `direction=FORWARD, focused_ratio 0.738, punch_travel 3.044 studs`; the
engine renders **0.191 stud** of forward travel and **2.111** of lateral. Z and X
essentially swapped. Reproduced across three character archetypes.

**After the fix the FK matches the engine to 0.0001 stud**, measured as
`hrp.CFrame:PointToObjectSpace(arm.CFrame * CFrame.new(0,-1,0))` while the
uploaded asset plays. That comparison is pinned as a regression test.

### 2. `root_translation` was inflating the verdict

Schema v2 lets an animation translate the HumanoidRootPart — the character's
step-in — and the FK applies that translation to every bone position. Both wrists
therefore inherit the body's forward motion. A step-in of up to 0.6 stud was on
its own enough to produce a `FORWARD` verdict while the arm barely moved.

Re-running the corpus with `root_translation` zeroed isolates the arm and is the
only honest way to ask "does the *strike* go forward".

### Corpus state after both fixes

Twelve authored seeds, arm-only (`root_translation` zeroed), disjoint buckets:

| bucket | n |
|---|---|
| clean (FORWARD + FOCUSED) | **5** |
| FORWARD but lateral (WARN/FAIL on focus) | **4** |
| BACKWARD | **3** |

No seed exceeds 1.4 stud of arm-only forward travel, against the 2.1–5.0 the
broken FK had been reporting.

A related integrity problem surfaced alongside: 8 of the 12 baked
`KeyframeSequence` assets predated a converter fix and no longer matched their
source — up to **41° of per-joint error** between the baked `Pose.CFrame` and
`CFrame.Angles(rx, ry, rz)` of the source. Six of the eight diverged in verdict
from their own source, one of them from clean-FORWARD to BACKWARD. They have been
re-baked to 0.0000°. Useful invariant: a `KeyframeSequence` `Pose.CFrame` **is**
the `Motor6D.Transform` the engine applies, so bake faithfulness is checkable
offline, without a running engine.

## Pose library

Labelled keyposes — `anticipation` / `contact` / `follow_through` / `recovery` —
mined from validated reference trajectories by detecting velocity peaks and
inversions on the striking wrist (computed through the same FK, so the library
and the judge share one convention).

Being repopulated from the **CMU Motion Capture Database** (public domain, free
for research and commercial use), whose combat subjects are indexed: subject 135
for martial-arts kicks and punches, subjects 138–142 for boxing. This replaces
earlier `TODO_extract` placeholders. Jab and hook are covered; roundhouse kick is
in progress.

## Capture pipeline

Visual verification runs through the **official Roblox Studio MCP server**, which
replaced a bespoke `CaptureService` + local-RPC script.

- Captures the 3D viewport in **Play mode** — the running game, not the editor.
- Camera is driven per shot as (position, look-at), so framing is deterministic
  without locking the camera on `RenderStepped`.
- Studio does **not** need to be the frontmost application, which removed a
  long-standing failure mode where the capture callback never fired.

One command starts Play, builds a throwaway capture rig, drives it through the
animation's key frames by writing `Motor6D.Transform`, captures each, tears the
rig down and returns to Edit. Each captured frame also emits an HRP-relative
effector probe, so a capture run doubles as a ground-truth check on the gate —
that probe is what caught bug #1.

Caveat worth knowing: with `StreamingEnabled`, a rig parked far from the player
has no `BaseParts` on the client (only the `Humanoid` replicates), so there is
nothing to render. The capture rig is placed directly above spawn.

## Reference code

[`reference-code/`](reference-code/) carries the forward-kinematics module and
the gate cascade. See its README for what is and is not runnable standalone.
