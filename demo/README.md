# Animal Arena Demo

This is the first playable Godot 4 prototype built around the seven plush
animal models in `models/glb/`. It combines a Pie Noon style throw / deflect /
survival loop with the local multiplayer, CPU opponent, and match result flow
used as references from Starship Olympics.

## 网页版

下载并解压 [Animal Arena Web ZIP](https://github.com/ZhongVikan/animal-companions-3d/raw/refs/heads/demo/animal-arena/downloads/Animal_Arena_Web.zip)。在解压目录运行 `python3 start_web.py`，Windows 可用 `py -3 start_web.py`。脚本会打开本机试玩地址，浏览器运行需要 WebGL 2。

电脑保留 1–4 人同屏键盘操作。触屏默认是单人对战 3 名 AI，横屏时左手拖动摇杆，右手投掷或按住格挡。

用 Godot **4.7.2** 和同版本的导出模板打开工程，可在 **项目 → 导出 → Web** 生成 `index.html`，或运行 `./demo/export_web.sh`。生成文件默认在 `build/web/`。将 `index.html` 和其他 `index.*` 文件一起托管，`index.wasm` 的 MIME 类型设为 `application/wasm`。Web 预设使用 Compatibility 渲染器和单线程，不需要 COOP/COEP 头。

后续以 Web 预设持续交付。游戏完成后，微信小游戏需要单独验证运行环境、触屏与生命周期、资源加载及包体限制，并在微信开发者工具和真机上测试。浏览器版和微信小游戏各自使用对应的打包流程。

## Run

Open the repository root in Godot 4.7.2 and press **Play**. Godot will
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
