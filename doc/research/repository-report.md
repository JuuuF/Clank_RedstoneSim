# Repository and toolchain report (Milestone 0)

Recorded 2026-10-10 at the start of the first agent session.

## Repository state found

| Item | Finding |
|---|---|
| Git | `main`, one commit `5e9bb5f Initial commit.` tracking only `.gitignore` and `README.md`. `doc/` was untracked and held a one-line placeholder `doc/README.md`, which the owner committed during the session as `60a1b78 Initial doc.` |
| `.gitignore` | Ignores `data/` entirely, so the JARs and decompiled sources are never committed. |
| Existing implementation | None. No Python code, no tests, no UI framework selected. |
| `data/prompt.md` | The project brief (the brief refers to it as `prompt.txt`; the actual file is `prompt.md`). |

## Supplied Minecraft artifacts (verified)

| Artifact | Contents | Verdict |
|---|---|---|
| `data/minecraft_jars/client.jar` | 34 227 entries, 10 737 `net/minecraft/**/*.class`, `Main-Class: net.minecraft.client.Main`. | Full client, includes the integrated server classes. |
| `data/minecraft_jars/server.jar` | 165 entries, `Main-Class: net.minecraft.bundler.Main`, `META-INF/versions/26.3/server-26.3.jar` plus `META-INF/libraries/**`. | **Bundler only**: it contains no game classes of its own. |
| `data/minecraft_jars/server-runtime.jar` | 18 557 entries, 7 744 game classes, `Main-Class: net.minecraft.server.Main`. | The real server. SHA-256 `a362163e…ae6` is identical to `META-INF/versions/26.3/server-26.3.jar` inside `server.jar` and to the hash in `META-INF/versions.list`. |
| `data/minecraft_src/client-src/` | 7 301 `.java` files, `version.json` id `26.3`, world version 5023, protocol 777, build time 2026-09-15. | Decompiled client JAR. |
| `data/minecraft_src/server-src/` | 5 037 `.java` files, same `version.json`. | Decompiled server runtime. |

Both trees use **Mojang's official names** (no obfuscation mapping is needed; for example
`net/minecraft/world/level/redstone/CollectingNeighborUpdater.java`). The decompiler output
uses `final` parameters and `var` naming typical of Vineflower/Fernflower; lambdas and
records are reconstructed well.

**Client vs. server divergence:** `diff -rq` over the two trees reports no file that exists in
both trees with different contents, and no server-only file. The server tree is a strict
subset of the client tree. All redstone, tick, and piston classes (`world/level/**`,
`server/level/**`, `world/ticks/**`) are byte-identical in both. Consequence: one tree is
enough for logic research; the documentation cites paths relative to
`data/minecraft_src/client-src/`, and they are equally valid for `server-src/`.

## Toolchain

| Tool | Version | Use |
|---|---|---|
| Python | 3.12.13 (Anaconda, `/home/justin/anaconda3/bin/python3`) | Application runtime. |
| PySide6 | 6.9.2 (Qt 6.9.2) | UI toolkit and OpenGL wrappers (see [[decisions#ADR-002]]). |
| numpy | 2.4.4 | Mesh building for the renderer. |
| pytest | 9.0.2 | Tests. |
| ruff, mypy | installed | Lint and type checks. |
| Java | `java`/`javap` default 1.8; JDK 8/11/17/21/25 under `/usr/lib/jvm` | Bytecode inspection if a decompiled method looks wrong (26.3 needs Java 25). |
| GPU | NVIDIA RTX 4060, OpenGL 4.6 core | Viewport. |

Display: Wayland session with XWayland (`DISPLAY=:0`). A PySide6 OpenGL prototype
(`QOffscreenSurface` + FBO, PySide6's own `QOpenGLShaderProgram`/`QOpenGLBuffer`) rendered
correctly with `QT_QPA_PLATFORM=xcb` and `offscreen`, but **failed to create a GL context on
the native `wayland` platform plugin** of this PySide6 build. The application therefore
defaults to `xcb` when it runs under Wayland and no platform is forced (see
[[implementation-notes]]).

## Related

- [[source-map]]: where each mechanic lives in the source.
- [[architecture]], [[decisions]], [[roadmap]].
