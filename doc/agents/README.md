# Working rules for agents

How to work on this project: the owner's standing instructions, with when and why they
were given and how to apply them. Before 2026-10-19 they lived in the coding agent's
private memory; they are here so the repository is self-contained. Anyone continuing the
work (an agent or a person) starts here, then goes to the mission they work on.

The rules are short; the state of the work is never here but in the pages they point to
(rule 3).

## Where to start

The repository holds two briefs; don't mix them up.

| Work | Brief | Live state |
|---|---|---|
| The simulator itself (porting, editor, CLI) | [[../README]] and [[../project-state]] | [[../project-state]], [[../roadmap]] |
| Redstone research: knowledge base, circuit library, contraptions | `PROMPT.md` (repository root; "use it as your main prompt", owner, 2026-10-16) | `PROMPT.md` "What exists now" and "TODO for the next agent"; [[../redstone/README]], [[../redstone/backlog]] |
| Piston-door reverse engineering | [[../redstone/doors/mission]] (the owner gave it as `data/redstone_learning/PROMPT.md`; "Do not use the root-level PROMPT.md: that's not for your task", 2026-10-18) | [[../redstone/doors/README]] ("Status and roadmap", open items D1–D12) and the mission's section 13 |

For the root research mission: read `PROMPT.md` §12 (resume steps), §13 (efficiency
rules and traps), §14 (sub-agents) and "What exists now", then [[../redstone/README]] and
the backlog. Don't redo finished work.

## Rules

1. **Everything simulated works exactly like the game** (owner, 2026-10-15: "everything
   HAS TO work exactly like in the game", after unmodeled furnaces were guessed
   pushable; documenting deviations is "an essential part of the project").
   - Any simulation change, above all a new block, is ported from `data/minecraft_src/`
     (cite class and method); never written from memory or from names. What can't be
     modeled exactly is stated, or the block stays foreign (inert).
   - Verify with a server scenario (`python -m tools.gameserver.run NAME`, rule 9) and
     keep the recording ([[../experiments/index]]). In research, verify new mechanics and
     finished compositions too (the recipe for a scenario from a CLI script is in
     `PROMPT.md` §13).
   - A deviation gets a `Not as in the game:` comment at the spot and an entry in
     [[../differences]] (game vs simulator, why, where, test).
   - In research, **never change the simulator to make an experiment pass**: a simulator
     bug is a finding.
2. **Fidelity first, from simple verified cases** (owner, 2026-10-10; ADR-010, ADR-011).
   Torch burnout is implemented (it is deterministic in 26.3). Test circuits start simple
   (door, sliding piston, lamp, inverters, AND gates) and build up. The wiki pages in
   `data/wiki/` are hints: re-verify every claim in the source or the game.
3. **The docs are the project's memory** (owner, 2026-10-11: "document the project state
   and architecture designs, current state etc. in the docs. Keep the short-term memory
   slim and the documented memory big"; ADR-012).
   - Update the docs in the same commit as the work: simulator: [[../README]] status,
     [[../project-state]], [[../decisions]], the mechanics pages, the experiments index;
     research: records, reference pages, backlog, `PROMPT.md` "What exists now"; doors:
     the doors README and the mission's section 13.
   - Owner, 2026-10-18: "Add your TODOs and state into the PROMPT.md … in order for other
     agents to keep on working on this later on." At the end of a session, update "What
     exists now" and its prioritized TODO list (concrete first steps: what to run, which
     case fails, where to look), and commit it with the docs. New traps go into
     `PROMPT.md` §13.
4. **Document each finding as soon as it is verified, and keep going** (owner,
   2026-10-19: "always document your important findings"; "always keep going
   automatically and report all your findings and progress before the quota runs out,
   so other agents can keep going seamlessly"; "make sure to have all ready to
   handoff"). Write the finding into the docs, commit and push it right away, not at the
   end; keep the open items current so a fresh agent can continue from the docs alone;
   don't stop to ask between steps.
5. **Git: a feature branch, push after every commit, `main` when it works** (owner,
   2026-10-10/12: "create feature branches with finer commits"; "if it's working, push
   it to main"; always have the latest version pushed to origin,
   `github.com:JuuuF/RedstoneSim`, especially when the quota may run out). `git push`
   the branch after each commit; when tests and ruff pass, `git push origin HEAD:main`.
   Check `git status` before committing: the owner may have staged files themselves.
6. **Export work as worlds the owner can open** (owner, 2026-10-17: "Whenever you find
   out something, can you export your findings? … Export what you are working on as
   .redsim.json files, so I can check them out myself. Even export things that did not
   work or are still work in progress"). After each finding or stage, save a world with
   a `note` (what it shows, works or not) in `experiments/wip/<topic>/`, list it in that
   folder's README.md, commit and push. Keep the failures. (Third-party designs are the
   exception: rule 10.)
7. **Don't get stuck** (owner, 2026-10-18: "Remember to not get stuck on a problem for
   too long if there are other areas to be tackled in the backlog, which might help you
   gain more knowledge"). After several attempts without a new result, write the state
   and the next ideas into the backlog and the topic's README, export the world (rule 6),
   commit, and take another item; come back later.
8. **Mind the quota** (owner, 2026-10-17: "I do not have too much quota, so maybe
   catting out big files is not too good of an idea"; sub-agents are worth it for
   isolated sub-tasks, "but only if that's actually a benefit").
   - Everything printed stays in the context: `grep -n "^##" FILE`, then `sed -n` one
     section; `redsim-cli help CMD`; filter script output (`sed -n '/^> check/,$p'`);
     `--dry-run`, named `waves` rows, `--json` with a script.
   - Delegate only a whole backlog item, a long verification run or a broad search;
     brief precisely, ask for a short report (about 200 words), review and commit the
     result yourself (`PROMPT.md` §14).
9. **The game server: sandboxed, for verification only** (owner, 2026-10-10, who
   accepted the EULA: "keep it as sandboxed as possible and only use for testing your
   implementation results and to test for game behavior"; ADR-008). Only through
   `tools/gameserver` (a throwaway, git-ignored folder in `.sandbox/`, offline mode,
   127.0.0.1, superflat, console commands). Never touch the owner's own installation or
   worlds; nothing beyond verification. One server run at a time (the world lock).
10. **`data/` is the owner's, and third-party designs stay out of git.** `data/` is
    git-ignored: the decompiled source (`minecraft_src/`), the game jars
    (`minecraft_jars/`), the wiki extract, saves, test worlds and the research datasets
    (`redstone_learning/`). Open them read-only and work on copies; never modify or
    rename the owner's files. Worlds and results derived from third-party designs go to
    `.sandbox/` (git-ignored) and are never committed; commit only the project's own
    designs, aggregate data and docs, and for a bug found in a third-party world a small
    scenario that isolates it.
11. **`[broken sim]` worlds are bug reports** (owner, 2026-10-18: "I've added some more
    worlds that did not work before … suffixed with '[broken sim].redsim.json'"; more can
    appear at any time). `find data/redstone_learning -name "*broken sim*"`; first scan
    the world's palette for blocks the simulator doesn't model and port them (rule 1),
    then run the whole world against the server with
    `python -m tools.gameserver.run_world WORLD` to find the real difference, and commit
    a small scenario that isolates it (results in `.sandbox/worlds/`). The three of
    2026-10-18 match the game now (EXP-068).
12. **Game assets come from the jar at runtime** (since 2026-10-11; ADR-023, ADR-024).
    The editor reads models, textures and the pixel font read-only from
    `data/minecraft_jars/client.jar` (`redsim.ui.assets`, `atlas`, `theme`). Never commit
    anything extracted from a jar; keep the `style.py` fallback working
    (`REDSIM_NO_GAME_ASSETS=1`); asset tests skip without the jar.
13. **Editor work follows the owner's UI direction** (nine feedback rounds, 2026-10-11 to
    13, all implemented, ADR-017–026; their status in [[../ui-direction]], every control
    in [[../controls]]). Ask the owner for priorities before new UI work.
    - Look: "mainly a Minecraft vibe, with Blender's UI in mind", dark; the jar's sprites
      where the game has the thing, else `pixel_icons`; never color emoji or mixed font
      glyphs. The first Minecraft-style fly controls were replaced by vim-like modes and
      a Blender-style orbit camera.
    - Check every visual change with a rendered screenshot; a 60 fps feel matters.
    - Editor operations (paste, move, rotate, …) cause no block updates; tick 0 is the
      build state.
    - When a default key changes, update `keymap.LEGACY_DEFAULTS`. A bug the owner reports
      gets a regression test; tests never touch the user's config folder.
14. **The piston-door mission's own rules** (owner, 2026-10-18/19).
    - Don't investigate LegDen's 7x7 and 8x8: the owner is removing them from the pool.
    - Keep the mission's section 13 (status and handoff) current at the end of a session.
      The tracked copy, [[../redstone/doors/mission]], is the one to edit;
      `data/redstone_learning/PROMPT.md` is the owner's original.
    - The traps learned on the way are in that section 13.

## Moving the project to another machine

Git holds the code, the docs and these rules. Copy `data/` as well (the source, the jars
and the datasets are needed and exist nowhere else), and `.sandbox/` if the slow results
should not be recomputed (`.sandbox/doors/`: the door-lab sweeps; `.sandbox/worlds/`: the
recorded game runs behind the experiments index; `.sandbox/gameserver/`: the configured
server). Then `pip install -e .` and, as a quick check, `pytest tests/doorlab`.
