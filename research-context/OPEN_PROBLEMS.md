# Open problems

Three problems open to external research. Background on the rig, the gate
cascade and the measurement conventions is in [`ARCHITECTURE.md`](ARCHITECTURE.md).

---

## 1. Synchronised two-character holds (R6)

**Goal.** Grabs, throws, grapples, clinches — any move where two R6 characters
are in sustained physical contact and the pair has to read as one choreographed
action rather than two animations happening near each other.

### What has been tried

A double-rig prototype. Two R6 characters animated **separately**, then the
contact brought into alignment by hand: sweeping the placement parameters
(relative offset and orientation of the two rigs, and the frame at which contact
occurs) until the contact distance dropped to an acceptable value.

It produced a contact that looked right for that one pairing.

### Why it stalls

The parameter sweep is a numerical fit, not choreography. It yields a set of
magic offsets for one animation pair at one relative placement, and there is no
representation of the *hold itself* to carry to the next move. Nothing learned in
one grapple transfers to another — the next one starts from a fresh sweep. The
approach does not scale past a handful of hand-tuned pairs.

What is missing is a way to author or generate a two-body action where the
contact constraint is part of the representation, so that a hold generalises
across moves, character placements, and — ideally — across the eight character
archetypes the project uses.

### Constraints a solution has to respect

- **R6 only.** Six joints, 3 rotational DOF each, no translation on the joints;
  root motion exists only as a HumanoidRootPart translation. There is no spine
  chain, no clavicles, no fingers. Hands are the bottom face of a 1×2×1 block —
  there is nothing to actually grip with, so "contact" is proximity plus a pose
  that reads as a grip.
- Roblox conventions: Y up, −Z forward, studs.
- Output must be `KeyframeSequence`-compatible, i.e. per-frame Euler angles on
  the six joints.
- Both characters are network-replicated and may be owned by different clients,
  so anything requiring frame-exact physical simulation on both sides is
  suspect. Prefer kinematic solutions.
- The single-character gate cascade in `ARCHITECTURE.md` does not apply to holds
  as written (it assumes a lone striker); a quality bar for two-body actions is
  itself part of the problem.

### Useful pointers

`reference-code/r6_fk.py` gives the exact R6 kinematics — part dimensions and the
real `C0`/`C1` attachment frames — needed to compute where a limb actually ends
up. Contact-distance math between two rigs should be built on it rather than on
assumed joint frames; see the C0/C1 note in `ARCHITECTURE.md` for why.

---

## 2. Procedural generation of playable environments

**Goal.** Generate playable arenas / environments for the game procedurally.

**Status: never attempted. No prior work of any kind.**

Open from the start: what the representation should be, whether generation is
grammar-based, solver-based, learned, or a hybrid, and how "playable" gets
defined and tested. Roblox-specific constraints (terrain vs. parts, streaming,
collision, spawn and navigation) are all still open questions rather than settled
requirements.

---

## 3. Webtoon → playable 3D style transfer

**Goal.** Take the visual language of a webtoon and carry it into a playable 3D
Roblox game — silhouettes, posing, panel-level readability, impact framing.

**Target reference: _The Player_.**

**Status: never attempted. No prior work of any kind.**

Open from the start: what "style" is being transferred (character design,
posing/animation vocabulary, shading and post-processing, camera and framing
language, or some combination), and how transfer fidelity would be measured
rather than eyeballed. Note that Roblox's rendering pipeline is a hard constraint
on the shading side, and that R6's six-part blocky body is a hard constraint on
the character-design side.

---

## Note on provenance

Sections 2 and 3 are declared greenfield by the project owner. Section 1's prior
attempt is reported from the owner's account of it; the prototype is not in this
repository. Everything in `ARCHITECTURE.md` is measured from the live codebase
and the running engine.
