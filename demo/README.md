# Animal Arena Demo

This is the first playable Godot 4 prototype built around the seven plush
animal models in `models/glb/`. It combines a Pie Noon style throw / deflect /
survival loop with the local multiplayer, CPU opponent, and match result flow
used as references from Starship Olympics.

## Run

Open the repository root in Godot 4.3 or newer and press **Play**. Godot will
import the seven GLBs on the first open; this can take a short while because
the models are textured static meshes.

At the title screen, press **1–4** to choose how many local human slots to
activate, then press **Enter**. Unfilled slots become CPU opponents. The match
is three rounds; the last living player wins a round, and the highest round
score wins the match.

Controls:

| Slot | Move | Throw | Block |
|---|---|---|---|
| P1 | WASD | F | Space |
| P2 | Arrow keys | Enter | Shift |
| P3 | IJKL | O | P |
| P4 | ZXCV | B | N |

The default match is one human and three CPUs. Pies bounce off the arena walls;
a successful block reflects a pie back toward its attacker. The CPU first
checks incoming danger, then moves toward a target and fires when in range.

## Headless smoke test

With Godot on `PATH`:

```bash
godot --headless --rendering-method gl_compatibility \
  --rendering-driver opengl3 --audio-driver Dummy --path . \
  -- --autostart --headless_test
```

The test starts a match, advances the simulation for five seconds, and prints
`HEADLESS_DEMO_TEST` with projectile and alive-player counts. It does not need
an external display. The repository's local test run used Godot 4.6.3 and
reported three throws with three players still alive after five seconds.
Use `--test_seconds=45` when you want to exercise a longer sequence of round
transitions.

## Prototype scope

- Four simultaneous player slots, with keyboard controls and CPU fill.
- The current build uses **three rounds**, a 42-second round
  timer, last-survivor win condition, round score, and match scoreboard.
- Manual projectile collision keeps the throw / hit loop deterministic and
  avoids requiring a physics rig for the static plush models.
- Characters are the supplied static GLB assets. They do not yet have bones,
  skinning, animation clips, ragdolls, or per-limb hitboxes.
- The arena, lighting, HUD, projectile visuals, and game logic are authored in
  this demo; no Starship Olympics art or audio is copied.

The reference-project license notes are in `THIRD_PARTY_NOTICES.md`.
