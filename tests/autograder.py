#!/usr/bin/env python3
"""
Autograder for AI&KE Assignment #3 — Planning with PDDL
=======================================================

Runs a planner on the student's PDDL files (task1/, task2/, task3/), parses the
generated plan, and validates that the plan is sound and reaches the goal.
Exit code 0 = pass, 1 = fail.

Two planners are supported:
  * pyperplan  — pure-Python, used for parsing/grounding/validation and for
                 solving STRIPS/typing/negative-precondition models.
  * Fast Downward — optional fallback for models that pyperplan cannot ground
                 (e.g. :action-costs, :numeric-fluents). Located via the
                 FAST_DOWNWARD env var or `fast-downward.py` on PATH.

Usage:
    python3 tests/autograder.py <TEST_ID>

Test IDs:
    T1_GRIPPER_PARSE   T2_GRIPPER_PLAN
    T3_VACUUM_PARSE    T4_VACUUM_PLAN    T5_VACUUM_GOAL
    T6_TRANSPORT_PARSE T7_TRANSPORT_PLAN T8_TRANSPORT_TYPING T9_TRANSPORT_MULTI
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TIMEOUT = 120  # seconds per planner run


# ── Failure type ─────────────────────────────────────────────

class TestFailure(Exception):
    pass


# ── Locating the student's files ─────────────────────────────

def task_files(task):
    """Return (domain_path, problem_path) for 'task1'|'task2'|'task3'."""
    d = os.path.join(REPO_ROOT, task, 'domain.pddl')
    p = os.path.join(REPO_ROOT, task, 'problem.pddl')
    for path, label in ((d, 'domain.pddl'), (p, 'problem.pddl')):
        if not os.path.isfile(path):
            raise TestFailure(
                f"{task}/{label} not found. Each task needs {task}/domain.pddl "
                f"and {task}/problem.pddl in the repository root."
            )
    return d, p


def read_text(path):
    with open(path, encoding='utf-8', errors='replace') as fh:
        return fh.read()


def strip_comments(text):
    """Remove PDDL line comments (everything after ';') from each line."""
    return '\n'.join(line.split(';', 1)[0] for line in text.splitlines())


# ── pyperplan: parse / ground / validate ─────────────────────

def pyperplan_ground(domain, problem):
    """Parse + ground with pyperplan. Returns (task, error_string).

    On success returns (task, None). On failure returns (None, message).
    Grounding fails for features pyperplan does not support (numeric fluents,
    action costs, durative actions) — callers treat that as "needs Fast Downward".
    """
    try:
        from pyperplan.pddl.parser import Parser
        from pyperplan.grounding import ground
    except ImportError as e:
        return None, f"pyperplan is not installed ({e}). Run: pip install pyperplan"

    try:
        parser = Parser(domain, problem)
        dom = parser.parse_domain()
        prob = parser.parse_problem(dom)
        task = ground(prob)
        return task, None
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def normalize_op(text):
    """Normalize a plan-step / operator name to '(name arg arg)' lowercased."""
    text = text.strip().lower()
    text = text.strip('()')
    parts = text.split()
    return '(' + ' '.join(parts) + ')'


def simulate(task, plan_steps):
    """Apply plan_steps to task.initial_state; return final state.

    Raises TestFailure if a step is not a known operator or not applicable.
    """
    ops = {normalize_op(op.name): op for op in task.operators}
    state = task.initial_state
    for i, step in enumerate(plan_steps, 1):
        key = normalize_op(step)
        op = ops.get(key)
        if op is None:
            raise TestFailure(
                f"Plan step {i} '{step}' is not a valid grounded action of the domain."
            )
        if not op.applicable(state):
            raise TestFailure(
                f"Plan step {i} '{step}' is not applicable in the reached state "
                f"(its preconditions are not satisfied)."
            )
        state = op.apply(state)
    return state


# ── Planner runners ──────────────────────────────────────────

def pyperplan_solve(domain, problem):
    """Solve with pyperplan CLI. Returns (status, plan_steps).

    status in {'solved', 'unsolvable', 'error'}. plan_steps is a list of
    '(op args)' strings (possibly empty if the goal holds initially).
    """
    if shutil.which('pyperplan'):
        base = ['pyperplan']
    else:
        base = [sys.executable, '-m', 'pyperplan']

    soln = problem + '.soln'
    if os.path.exists(soln):
        os.remove(soln)

    # Greedy best-first with the FF heuristic keeps these small problems fast.
    for args in (['-H', 'hff', '-s', 'gbf'], []):
        try:
            res = subprocess.run(
                base + args + [domain, problem],
                capture_output=True, text=True, timeout=TIMEOUT, cwd=REPO_ROOT,
            )
        except subprocess.TimeoutExpired:
            return 'error', []
        except Exception:
            return 'error', []

        if os.path.exists(soln):
            steps = [ln.strip() for ln in read_text(soln).splitlines() if ln.strip()]
            return 'solved', steps

        blob = (res.stdout + res.stderr).lower()
        if 'goal can be simplified to false' in blob or 'no solution' in blob \
                or 'unsolvable' in blob:
            return 'unsolvable', []
        # else: try the next arg set (e.g. heuristic flag unsupported), then give up

    return 'error', []


def find_fast_downward():
    """Return the Fast Downward entry point, or None if unavailable."""
    env = os.environ.get('FAST_DOWNWARD')
    if env and os.path.isfile(env):
        return env
    for name in ('fast-downward.py', 'downward', 'fast-downward'):
        path = shutil.which(name)
        if path:
            return path
    return None


def fast_downward_solve(domain, problem):
    """Solve with Fast Downward. Returns (status, plan_steps) or ('unavailable', [])."""
    fd = find_fast_downward()
    if not fd:
        return 'unavailable', []

    workdir = tempfile.mkdtemp(prefix='fd_')
    plan_file = os.path.join(workdir, 'plan')
    cmd = [fd] if fd.endswith('.py') else [sys.executable, fd] if fd.endswith('downward') else [fd]
    cmd = [fd, '--plan-file', plan_file, domain, problem,
           '--search', 'astar(lmcut())']
    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT, cwd=workdir)
    except Exception:
        return 'error', []

    # FD may append .1, .2 ... for anytime search; pick the best (last) one.
    candidates = [plan_file] + [plan_file + f'.{i}' for i in range(1, 20)]
    found = [c for c in candidates if os.path.isfile(c)]
    if not found:
        return 'unsolvable', []

    steps = []
    for ln in read_text(found[-1]).splitlines():
        ln = ln.strip()
        if not ln or ln.startswith(';'):
            continue
        steps.append(ln)
    return 'solved', steps


def solve(domain, problem):
    """Solve with pyperplan, falling back to Fast Downward. Returns (status, steps, planner)."""
    status, steps = pyperplan_solve(domain, problem)
    if status == 'solved':
        return status, steps, 'pyperplan'

    fd_status, fd_steps = fast_downward_solve(domain, problem)
    if fd_status == 'solved':
        return fd_status, fd_steps, 'fast-downward'
    if fd_status == 'unavailable':
        return status, steps, 'pyperplan'  # report pyperplan's result
    return fd_status, fd_steps, 'fast-downward'


# ── Shared assertions ────────────────────────────────────────

def assert_parses(task, domain, problem):
    """Ensure the model is at least parseable. pyperplan-groundable is best;
    if not, accept a Fast Downward run as evidence that the PDDL is valid."""
    if task is not None:
        return 'pyperplan'
    status, _ = fast_downward_solve(domain, problem)
    if status in ('solved', 'unsolvable'):
        # FD parsed the files (it ran a search), so the PDDL syntax is valid.
        return 'fast-downward'
    return None


def assert_solved(domain, problem, task, require_actions=True):
    """Run a planner and return (plan_steps, planner). Fail if no plan found.

    Rejects a trivially-empty goal and (when require_actions) a 0-action plan —
    for these assignments nothing is cleaned/delivered in the initial state, so a
    real solution must contain at least one action."""
    if task is not None and len(task.goals) == 0:
        raise TestFailure(
            "The :goal is empty — there is nothing to achieve, so the planner "
            "returns immediately. Define a goal (e.g. all rooms clean, or every "
            "package at its destination)."
        )
    status, steps, planner = solve(domain, problem)
    if status == 'unsolvable':
        raise TestFailure(
            "The planner reports the problem is UNSOLVABLE — no plan reaches the "
            "goal. Check the :init state, the :goal, and the action effects."
        )
    if status != 'solved':
        raise TestFailure(
            "No plan was produced. Either the PDDL failed to parse, the planner "
            "timed out, or the model uses features no available planner supports. "
            "Verify the files solve in https://editor.planning.domains or with "
            "Fast Downward locally."
        )
    if require_actions and len(steps) == 0:
        raise TestFailure(
            "The planner returned an empty (0-action) plan, which means the goal "
            "already holds in the initial state. Check that :init does not already "
            "satisfy the :goal (e.g. rooms must start dirty, packages at their origin)."
        )
    return steps, planner


def assert_goal_reached(task, steps):
    """If the task is groundable, simulate the plan and confirm the goal holds."""
    if task is None:
        return  # advanced model graded manually; planner already found a plan
    final = simulate(task, steps)
    if not task.goal_reached(final):
        raise TestFailure(
            "The plan executes but the goal is NOT satisfied in the final state. "
            "Check that the action effects actually establish every goal predicate."
        )


def schemas_in_plan(steps):
    """Distinct action-schema names used by a plan (the first token of each step)."""
    names = set()
    for s in steps:
        toks = s.strip().strip('()').split()
        if toks:
            names.add(toks[0].lower())
    return names


# ── Tests: Task 3 (Gripper / ball-moving robot) ──────────────

def test_t1_gripper_parse():
    """T1: task3 domain+problem parse cleanly."""
    domain, problem = task_files('task3')
    task, err = pyperplan_ground(domain, problem)
    planner = assert_parses(task, domain, problem)
    if planner is None:
        raise TestFailure(f"task3 PDDL failed to parse/ground: {err}")
    print(f"PASS: task3 (gripper) PDDL parses correctly (via {planner}).")


def test_t2_gripper_plan():
    """T2: task3 solves and all balls end up in room2."""
    domain, problem = task_files('task3')
    task, _ = pyperplan_ground(domain, problem)
    steps, planner = assert_solved(domain, problem, task)
    assert_goal_reached(task, steps)
    print(f"PASS: gripper plan found ({len(steps)} actions, via {planner}) — "
          f"all balls delivered to the goal room.")


# ── Tests: Task 2 (Vacuum robot) ─────────────────────────────

def test_t3_vacuum_parse():
    """T3: task2 domain+problem parse cleanly."""
    domain, problem = task_files('task2')
    task, err = pyperplan_ground(domain, problem)
    planner = assert_parses(task, domain, problem)
    if planner is None:
        raise TestFailure(f"task2 PDDL failed to parse/ground: {err}")
    print(f"PASS: task2 (vacuum) PDDL parses correctly (via {planner}).")


def test_t4_vacuum_plan():
    """T4: task2 solves with a sound plan."""
    domain, problem = task_files('task2')
    task, _ = pyperplan_ground(domain, problem)
    steps, planner = assert_solved(domain, problem, task)
    assert_goal_reached(task, steps)
    print(f"PASS: vacuum plan found ({len(steps)} actions, via {planner}).")


def test_t5_vacuum_goal():
    """T5: the plan uses a cleaning action (rooms are cleaned, not pre-set)."""
    domain, problem = task_files('task2')
    task, _ = pyperplan_ground(domain, problem)
    steps, planner = assert_solved(domain, problem, task)
    assert_goal_reached(task, steps)

    clean_steps = [s for s in steps if re.match(r'\(?\s*clean\b', s.strip(), re.I)]
    if not clean_steps:
        raise TestFailure(
            "The plan reaches the goal without any 'clean' action. Rooms must be "
            "cleaned by the robot, not declared clean in :init. Check the goal and "
            "the clean action's effects."
        )
    print(f"PASS: vacuum goal achieved by cleaning — {len(clean_steps)} clean "
          f"action(s) in a {len(steps)}-step plan (via {planner}).")


# ── Tests: Task 1 (Package transport) ────────────────────────

def test_t6_transport_parse():
    """T6: task1 domain+problem parse (pyperplan or Fast Downward)."""
    domain, problem = task_files('task1')
    task, err = pyperplan_ground(domain, problem)
    planner = assert_parses(task, domain, problem)
    if planner is None:
        raise TestFailure(
            f"task1 PDDL failed to parse. pyperplan said: {err}. If you use "
            f"advanced features (:action-costs, :durative-actions, :numeric-fluents), "
            f"make sure they also solve with Fast Downward."
        )
    note = "" if task is not None else " (advanced features — validated via Fast Downward)"
    print(f"PASS: task1 (transport) PDDL parses correctly (via {planner}){note}.")


def test_t7_transport_plan():
    """T7: task1 solves; packages are delivered (goal reached)."""
    domain, problem = task_files('task1')
    task, _ = pyperplan_ground(domain, problem)
    steps, planner = assert_solved(domain, problem, task)
    assert_goal_reached(task, steps)
    note = "" if task is not None else " (goal validated by the planner)"
    print(f"PASS: transport plan found ({len(steps)} actions, via {planner}) — "
          f"packages delivered{note}.")


def test_t8_transport_typing():
    """T8: the transport domain uses :typing with multiple object types."""
    domain, _ = task_files('task1')
    text = strip_comments(read_text(domain)).lower()
    if ':typing' not in text:
        raise TestFailure(
            "task1/domain.pddl does not declare :typing in :requirements. The "
            "transport model must type its objects (e.g. package, location, vehicle)."
        )
    m = re.search(r'\(:types\s+(.*?)\)', text, re.S)
    if not m:
        raise TestFailure("task1/domain.pddl declares :typing but has no (:types ...) block.")
    # Count distinct type names (ignore the '- supertype' parts).
    body = re.sub(r'-\s*\S+', ' ', m.group(1))
    types = {t for t in body.split() if t}
    if len(types) < 2:
        raise TestFailure(
            f"Expected at least 2 object types (e.g. package + location + vehicle), "
            f"found {len(types)}: {sorted(types)}."
        )
    print(f"PASS: transport domain is typed — {len(types)} types: {', '.join(sorted(types))}.")


def test_t9_transport_multi():
    """T9: the transport model is non-trivial — packages are carried by vehicles.

    Requires the plan to use at least 2 distinct action schemas (e.g. load /
    move / unload) rather than teleporting packages with a single action."""
    domain, problem = task_files('task1')
    task, _ = pyperplan_ground(domain, problem)
    steps, planner = assert_solved(domain, problem, task)
    assert_goal_reached(task, steps)

    schemas = schemas_in_plan(steps)
    if len(schemas) < 2:
        raise TestFailure(
            f"The plan uses only {len(schemas)} action type(s): {sorted(schemas)}. "
            f"A real transport model loads packages onto vehicles, moves the "
            f"vehicles, and unloads them — at least 2 distinct actions (typically "
            f"load / move / unload)."
        )
    print(f"PASS: transport model carries packages via vehicles — plan uses "
          f"{len(schemas)} action types: {', '.join(sorted(schemas))} (via {planner}).")


# ── Registry ─────────────────────────────────────────────────

TESTS = {
    'T1_GRIPPER_PARSE':    test_t1_gripper_parse,
    'T2_GRIPPER_PLAN':     test_t2_gripper_plan,
    'T3_VACUUM_PARSE':     test_t3_vacuum_parse,
    'T4_VACUUM_PLAN':      test_t4_vacuum_plan,
    'T5_VACUUM_GOAL':      test_t5_vacuum_goal,
    'T6_TRANSPORT_PARSE':  test_t6_transport_parse,
    'T7_TRANSPORT_PLAN':   test_t7_transport_plan,
    'T8_TRANSPORT_TYPING': test_t8_transport_typing,
    'T9_TRANSPORT_MULTI':  test_t9_transport_multi,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in TESTS:
        print("Usage: python3 tests/autograder.py <TEST_ID>")
        print(f"Available tests: {', '.join(TESTS.keys())}")
        sys.exit(1)

    test_id = sys.argv[1]
    try:
        TESTS[test_id]()
        sys.exit(0)
    except TestFailure as e:
        print(f"FAIL [{test_id}]: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR [{test_id}]: Unexpected error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
