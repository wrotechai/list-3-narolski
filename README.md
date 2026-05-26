# Assignment #3 — Planning with PDDL

**Course:** Artificial Intelligence and Knowledge Engineering (AI&KE), 2025/2026, SI4024L

---

## Overview

In this assignment you model three planning problems in **PDDL** (Planning Domain
Definition Language) and solve them with a planner. Each problem has a **domain**
file (the actions and predicates) and a **problem** file (the objects, initial
state, and goal).

| Task | Problem | Points |
|------|---------|--------|
| **Task 1** | Package transport (logistics) — design a transport model, optionally with PDDL extensions (costs, durations, multiple transport modes). | 25 |
| **Task 2** | Vacuum robot — visit all rooms and clean them. | 15 |
| **Task 3** | Ball-moving robot (gripper) — move four balls between two rooms. The PDDL is **provided**; run it and analyse the plan. | 10 |

See the assignment PDF for full details, scoring, and theoretical background.

---

## Repository structure

```
.
├── task1/
│   ├── domain.pddl          # Package transport — write your model here
│   └── problem.pddl
├── task2/
│   ├── domain.pddl          # Vacuum robot — write your model here
│   └── problem.pddl
├── task3/
│   ├── domain.pddl          # Gripper — PROVIDED, run and analyse
│   └── problem.pddl
├── tests/
│   └── autograder.py        # Automated tests (DO NOT MODIFY)
├── .github/                 # CI / autograding config (DO NOT MODIFY)
└── README.md
```

**Keep this layout.** The autograder expects each task's files at
`task<N>/domain.pddl` and `task<N>/problem.pddl`.

---

## How to run a planner

You can use any PDDL planner. Two convenient options:

- **Online editor** — paste your files into <https://editor.planning.domains> and
  click *Solve*. Fastest way to iterate.
- **Fast Downward** (local):
  ```bash
  fast-downward.py task2/domain.pddl task2/problem.pddl --search "astar(lmcut())"
  ```
- **pyperplan** (local, pure Python — this is what CI uses for STRIPS/typing models):
  ```bash
  pip install pyperplan
  pyperplan task2/domain.pddl task2/problem.pddl     # writes task2/problem.pddl.soln
  ```

> The autograder in CI solves with **pyperplan** and falls back to **Fast Downward**
> for models that use features pyperplan cannot handle (`:action-costs`,
> `:durative-actions`, `:numeric-fluents`). pyperplan supports `:strips`,
> `:typing`, and `:negative-preconditions`.

---

## How to submit your solution

### 1. Clone this repository
```bash
git clone <your-repo-url>
cd <your-repo-name>
```

### 2. Fill in the PDDL files
- **Task 1** (`task1/`): design the transport domain + problem. At minimum, model
  loading packages onto vehicles, moving the vehicles, and unloading — packages
  must be *carried*, not teleported. Use the typing requirement. Extensions
  (costs, durations, multiple transport modes) are encouraged and graded in the
  report.
- **Task 2** (`task2/`): the move + clean domain and a problem with the robot and
  rooms `pokoj1`, `pokoj2`, `pokoj3`; the goal is all rooms clean.
- **Task 3** (`task3/`): already provided. You only need to run it and analyse the
  plan for the report.

### 3. Push your solution
```bash
git add .
git commit -m "Add my PDDL solution"
git push
```

Every push triggers the **autograder** via GitHub Actions. Check the results in the
**Actions** tab of your repository.

---

## Autograder tests

The autograder runs 9 tests (40 points). It verifies that your PDDL **parses**,
that the planner **finds a plan**, and that the plan **actually reaches the goal**.
These tests do **not** determine your final grade.

> **The final grade is determined by the teacher** based on the autograder results,
> the quality of your report (problem description, plan screenshots, experiment
> analysis, conclusions), and your understanding of PDDL and planning. Passing all
> autograder tests is necessary but not sufficient for a full score. See the
> grading rubric for the complete breakdown.

| Test | What it checks | Points |
|------|---------------|--------|
| T1_GRIPPER_PARSE   | Task 3 PDDL parses | 2 |
| T2_GRIPPER_PLAN    | Gripper plan reaches the goal (balls moved to room2) | 5 |
| T3_VACUUM_PARSE    | Task 2 PDDL parses | 2 |
| T4_VACUUM_PLAN     | Vacuum plan is sound and reaches the goal | 5 |
| T5_VACUUM_GOAL     | Rooms are cleaned by a `clean` action (not pre-set) | 5 |
| T6_TRANSPORT_PARSE | Task 1 PDDL parses | 3 |
| T7_TRANSPORT_PLAN  | Transport plan delivers the packages | 7 |
| T8_TRANSPORT_TYPING| Transport domain is typed with multiple types | 5 |
| T9_TRANSPORT_MULTI | Packages are carried by vehicles (load / move / unload) | 6 |

### Running tests locally

```bash
pip install pyperplan          # (and optionally build Fast Downward)
python3 tests/autograder.py T2_GRIPPER_PLAN

# Run all tests:
for t in T1_GRIPPER_PARSE T2_GRIPPER_PLAN T3_VACUUM_PARSE T4_VACUUM_PLAN \
         T5_VACUUM_GOAL T6_TRANSPORT_PARSE T7_TRANSPORT_PLAN \
         T8_TRANSPORT_TYPING T9_TRANSPORT_MULTI; do
    echo "--- $t ---"
    python3 tests/autograder.py $t
done
```

---

## Report

Your report must include, for each task: the **problem description**, a
**screenshot of the generated plan**, an **analysis of experiments** (plan length,
cost, computation time, the effect of the transport topology for Task 1), and
**conclusions** — together with the `.pddl` files.

---

## Important notes

- **Do not modify** files in `tests/` or `.github/`. Changes to these protected
  files will be flagged.
- Keep the `task1/ task2/ task3/` layout with `domain.pddl` + `problem.pddl` in each.
- Task 1 must use `:typing` and carry packages with vehicles. Advanced extensions
  are graded in the report.

---

## Helpful resources

- Online editor: <https://editor.planning.domains>
- Fast Downward: <https://www.fast-downward.org/>
- PDDL reference: <https://planning.wiki/ref/pddl/domain>
- Learn PDDL: <https://fareskalaboud.github.io/LearnPDDL/>

## Quick Git reference

| What you want to do | Command |
|---------------------|---------|
| Clone your repo | `git clone <url>` |
| Check what changed | `git status` |
| Stage files | `git add task1 task2 task3` |
| Commit | `git commit -m "description"` |
| Push to GitHub | `git push` |
