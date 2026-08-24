# Reference code

Two files lifted verbatim from the project. Nothing else from the codebase is here.

## `r6_fk.py` — standalone, runnable

Pure-math forward kinematics for R6 `Motor6D` animations. Only dependency is
numpy. This is the file most likely to be useful for the two-character-holds
problem: it carries the engine-canonical R6 part dimensions and, importantly, the
**real `C0`/`C1` attachment frames including their rotations** — the thing that
was wrong for months and that any contact-distance math between two rigs depends
on. See the bug write-up in [`../ARCHITECTURE.md`](../ARCHITECTURE.md).

```python
from r6_fk import pose_to_bone_positions, motor6d_frames_to_bone_positions

# one pose -> world positions of 7 bones + 5 effector tips, HRP-relative
pose_to_bone_positions({"Right Shoulder": {"rx": 0, "ry": 0, "rz": 90}})
# -> {..., "Right Wrist": {"x": 1.5, "y": 0.5, "z": -1.5}, ...}
```

Verified against positions measured inside the running Roblox engine to
**0.0001 stud**.

## `stage4_gate_cascade.py` — excerpt, not runnable as-is

The deterministic judge described in `ARCHITECTURE.md`. Included so the accept /
reject criteria and their thresholds are readable in full rather than
paraphrased.

It will not run standalone: it imports `stage_marketplace_metrics` (timing
metrics and the golden reference) and reads the project's `golden_set/` data,
neither of which is published here. Read `run_cascade()` and `_fk_metrics()` for
the logic; treat the module-level constants as the calibrated thresholds.

Note it is only a judge for *single-character strikes*. A quality bar for
two-body holds does not exist yet and is part of open problem #1.
