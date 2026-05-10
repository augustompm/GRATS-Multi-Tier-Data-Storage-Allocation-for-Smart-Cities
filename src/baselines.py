import json
from pathlib import Path

import pulp as pl

from .parameters import AGENTS
from .objectives import q1_cost, q2_latency, q3_co2

RESULTS_DIR = Path(__file__).parent.parent / 'results'


def evaluate(assignment, roles, role_keys):
    q1 = sum(q1_cost(assignment[k], roles[k]) for k in role_keys)
    q2 = sum(q2_latency(assignment[k], roles[k]) for k in role_keys)
    q3 = sum(q3_co2(assignment[k], roles[k]) for k in role_keys)
    return q1, q2, q3


def assignment_count(assignment):
    counts = {a: 0 for a in AGENTS}
    for k, a in assignment.items():
        counts[a] += 1
    return counts


def b1_lifecycle(roles, role_keys):
    sub_to_agent = {
        'Live': 'Toronto-OnPrem-SSD-Hot',
        'Recent': 'Toronto-OnPrem-HDD-Warm',
        'Archive': 'Toronto-OnPrem-Tape-Cold',
    }
    out = {}
    for k in role_keys:
        role = roles[k]
        if role['class_label'] == 'open':
            out[k] = 'Toronto-OnPrem-SSD-Hot'
        else:
            out[k] = sub_to_agent[role['sub_tier']]
    return out


def b2_mono_cost(roles, role_keys):
    agent_keys = list(AGENTS.keys())
    m, n = len(agent_keys), len(role_keys)
    prob = pl.LpProblem('B2', pl.LpMinimize)
    T = {(i, j): pl.LpVariable(f'T_{i}_{j}', cat='Binary') for i in range(m) for j in range(n)}
    prob += pl.lpSum(q1_cost(agent_keys[i], roles[role_keys[j]]) * T[(i, j)] for i in range(m) for j in range(n))
    for j in range(n):
        prob += pl.lpSum(T[(i, j)] for i in range(m)) == 1
    for j in range(n):
        if roles[role_keys[j]].get('class_label') == 'operational':
            for i in range(m):
                if AGENTS[agent_keys[i]]['region_grid'] == 'RFCW':
                    prob += T[(i, j)] == 0
    for j in range(n):
        cap = roles[role_keys[j]].get('c4_max_latency_s', float('inf'))
        cap = float('inf') if cap is None else float(cap)
        for i in range(m):
            if AGENTS[agent_keys[i]]['latency_s'] > cap:
                prob += T[(i, j)] == 0
    prob.solve(pl.PULP_CBC_CMD(msg=False, timeLimit=120))
    return {role_keys[j]: agent_keys[i]
            for j in range(n)
            for i in range(m)
            if T[(i, j)].value() > 0.5}


def b3_all_ssd_hot(role_keys):
    return {k: 'Toronto-OnPrem-SSD-Hot' for k in role_keys}


def dominates(a, b, rel_tol=1e-9):
    def leq(x, y): return x <= y + rel_tol * max(abs(x), abs(y), 1.0)
    def lt(x, y):  return x < y - rel_tol * max(abs(x), abs(y), 1.0)
    return all(leq(a[k], b[k]) for k in range(3)) and any(lt(a[k], b[k]) for k in range(3))


def validate_no_dominance(baselines, pareto):
    for name, bq in baselines.items():
        for i, p in enumerate(pareto):
            if dominates((bq['Q1'], bq['Q2'], bq['Q3']), (p['Q1'], p['Q2'], p['Q3'])):
                return False, f'{name} dominates pareto[{i}]'
    return True, None


def run(instance=None, pareto=None, write=True):
    if instance is None:
        instance = json.loads((RESULTS_DIR / 'instance_toronto.json').read_text(encoding='utf-8'))
    if pareto is None:
        pareto = json.loads((RESULTS_DIR / 'pareto_k20.json').read_text(encoding='utf-8'))
    roles = instance['role_details']
    role_keys = instance['role_keys']

    a1 = b1_lifecycle(roles, role_keys)
    a2 = b2_mono_cost(roles, role_keys)
    a3 = b3_all_ssd_hot(role_keys)

    q1_b1, q2_b1, q3_b1 = evaluate(a1, roles, role_keys)
    q1_b2, q2_b2, q3_b2 = evaluate(a2, roles, role_keys)
    q1_b3, q2_b3, q3_b3 = evaluate(a3, roles, role_keys)

    baselines = {
        'B1_Lifecycle_OnPrem': {'Q1': q1_b1, 'Q2': q2_b1, 'Q3': q3_b1, 'distribution': assignment_count(a1)},
        'B2_Mono_Cost':        {'Q1': q1_b2, 'Q2': q2_b2, 'Q3': q3_b2, 'distribution': assignment_count(a2)},
        'B3_All_SSD_Hot':      {'Q1': q1_b3, 'Q2': q2_b3, 'Q3': q3_b3, 'distribution': assignment_count(a3)},
    }

    v_ok, v_msg = validate_no_dominance(baselines, pareto['pareto_front'])
    lex_q1 = pareto['extremes']['Q1']['Q1']
    b2_match = abs(q1_b2 - lex_q1) / max(abs(lex_q1), 1e-9) < 1e-6

    out = {
        'baselines': baselines,
        'validations': {
            'no_dominance': v_ok,
            'no_dominance_msg': v_msg,
            'b2_matches_lex_q1': b2_match,
        },
    }
    if write:
        path = RESULTS_DIR / 'baselines.json'
        path.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=str), encoding='utf-8')
    return out


if __name__ == '__main__':
    out = run()
    for name, q in out['baselines'].items():
        print(f'{name} Q1={q["Q1"]:.0f} Q2={q["Q2"]:.0f} Q3={q["Q3"]:.0f}')
