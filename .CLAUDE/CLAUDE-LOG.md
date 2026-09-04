# Claude Log

## 2026-09-04 — Repo turned into BeetleBot lab-prep workspace

- Read `.CLAUDE/` (CLAUDE.md, CLAUDE-COMMON.md, PROJ_STARTER.md, CLAUDE-LOG.md, skills) and all four handouts in `docs/`.
- Fetched the BeetleBot repo overview and the ROS 2 Jazzy tutorial URLs from the web.
- **Decisions (agreed with user):**
  - BeetleBot source included as a plain `git clone` into `BeetleBot/`, added to a new root `.gitignore`. Not a submodule, not vendored. User updates it with `git pull`.
  - Learning guides written "lab-exam focused" — CLI tools, topics/services, `rclpy`, `colcon`, bags, SLAM basics; not the full DDS/QoS/URDF treatment.
- **Files created:**
  - `.gitignore` — ignores `BeetleBot/`, colcon `build/install/log`, Python/editor cruft, rosbags.
  - `README.md` — repo purpose, layout, study order.
  - `learn/01-linux-commands.md` — terminal commands used across the lab.
  - `learn/02-ros2-concepts.md` — ROS 2 model + `rclpy` node anatomy, walking through the handout obstacle-avoidance script.
  - `learn/03-beetlebot-runbook.md` — consolidated lab-day procedure, reconciling the four handouts.
  - `learn/04-ros2-official-docs.md` — curated index into docs.ros.org/en/jazzy.
- **Files rewritten:**
  - `.CLAUDE/CLAUDE.md` — from library-template to real project brief for this repo.
  - `TODO.md` / `.CLAUDE/CLAUDE-LOG.md` — filled from empty.
- **Left incomplete / open questions:**
  - The handouts disagree on robot identity (IP `192.168.0.128` vs `.129` vs `.bot_No`; hostname `beetlebot-124.local`; Wi-Fi password truncated `15619xxx`; drive topic `/cmd_vel_nav` in handouts vs `/cmd_vel` in the upstream repo). Recorded as technical debt in `CLAUDE.md`; user to confirm with instructor.
  - Nothing committed yet — waiting on user.

## 2026-09-04 — Added JetBot and Acrux reference clones

- User asked to clone `NVIDIA-AI-IOT/jetbot` and `VEEROBOT/acrux` the same way `BeetleBot/`
  was cloned (comparison reference only — not part of the lab robot), and to record all
  three repo links in `README.md`.
- Verified both remote URLs with `git ls-remote` before cloning.
- **Files created (gitignored, not tracked):** `jetbot/`, `acrux/` — plain `git clone`s at
  repo root.
- **Files changed:**
  - `.gitignore` — added `jetbot/` and `acrux/` ignore blocks, same style as `BeetleBot/`.
  - `README.md` — added both to the Layout table; replaced the single-repo "Get / refresh
    the BeetleBot source" section with a three-repo table + clone commands for all of
    BeetleBot, JetBot, Acrux.
  - `TODO.md` — logged the addition under Done.
- Did **not** touch `.CLAUDE/CLAUDE.md`'s architecture/robot narrative — jetbot/acrux are
  reference clones only, not part of the BeetleBot lab workflow.

## 2026-09-04 — Course syllabus + lab-day study guides

- User asked to read the two course syllabus PDFs in `docs/` plus every other handout, and
  produce study material organized around the three actual lab sessions (Lab 1: turtlesim
  publish/subscribe, Lab 2: movement commands, Lab 3: obstacle avoidance) with the "why"
  for every command, not just the "what".
- Extracted PDF/docx text with `pdftotext -layout` and a small inline Python
  zipfile/regex script (no `python-docx` available) since `pdftoppm`/image rendering
  wasn't installed.
- **Finding:** `learn/01-04` already covered most of the mechanics (CLI reference, ROS 2
  concepts + colcon + a full line-by-line read of the "Updated" obstacle-avoidance node,
  and a fully reconciled runbook). Decided against one new file per raw `docs/` document
  (would have mostly re-pasted `01-04`) and instead wrote thin, cross-linked, lab-day
  checklist files plus one genuinely new file for content nothing else covered.
- **Files created:**
  - `learn/00-course-and-lab-map.md` — what the two syllabus PDFs (`BMHA314E` practical
    variant with a "List of Experiments", `BMHA314L` theory-only variant) actually require,
    plus a table mapping every `docs/` file to its lab day and covering `learn/` file.
  - `learn/05-lab1-turtlesim-and-workspace.md` — Lab 1 checklist (workspace, turtlesim
    pub/sub), cross-linking `01`/`02` instead of re-explaining CLI/colcon mechanics.
  - `learn/06-lab2-beetlebot-movement.md` — Lab 2 checklist (connect/arm/drive/teleop),
    with the `Twist` field meanings and the `-r`/`-t`/`&&` movement-recipe pattern spelled
    out, cross-linking `03-beetlebot-runbook.md` for the full reconciled procedure.
  - `learn/07-lab3-obstacle-avoidance.md` — Lab 3 checklist (deploy/register/build/run the
    node), plus a side-by-side comparison of the plain vs "Updated" obstacle-avoidance
    scripts (zones, thresholds, fixed-vs-compared turn direction, timed reverse) — this
    comparison didn't exist anywhere else in the repo.
- **Files changed:**
  - `README.md` — study order now starts at `00`, splits into "reference guides" (`01-04`)
    and "lab-day checklists" (`05-07`).
  - `.CLAUDE/CLAUDE.md` — Architecture table lists the four new `learn/` files and the
    `jetbot/`/`acrux/` reference clones.
  - `TODO.md` — logged under Done.
- Left `02-ros2-concepts.md` §5 as the canonical line-by-line code walkthrough (not
  duplicated into `07`) and `03-beetlebot-runbook.md` as the canonical single-session
  procedure (not duplicated into `05`/`06`) — the new files link to both instead.
