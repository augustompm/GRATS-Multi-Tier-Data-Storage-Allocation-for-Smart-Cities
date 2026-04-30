"""Exact Pareto frontier via epsilon-constraint with AUGMECON in CBC."""

import argparse
import json
import time
from pathlib import Path

import pulp as pl

from .parameters import AGENTS
from .objectives import q1_cost, q2_latency, q3_co2

RESULTS_DIR = Path(__file__).parent.parent / 'results'


def role_max_latency(role):
    v = role.get('c4_max_latency_s')
    return float('inf') if v is None or v == float('inf') else float(v)


def build_lp(roles, role_keys, eps2=None, eps3=None, primary='Q1', augmecon=False, ranges=None):
    agent_keys = list(AGENTS.keys())
    m, n = len(agent_keys), len(role_keys)
    prob = pl.LpProblem('GRATS', pl.LpMinimize)
    T = {(i, j): pl.LpVariable(f'T_{i}_{j}', cat='Binary') for i in range(m) for j in range(n)}

    e1 = pl.lpSum(q1_cost(agent_keys[i], roles[role_keys[j]]) * T[(i, j)] for i in range(m) for j in range(n))
    e2 = pl.lpSum(q2_latency(agent_keys[i], roles[role_keys[j]]) * T[(i, j)] for i in range(m) for j in range(n))
    e3 = pl.lpSum(q3_co2(agent_keys[i], roles[role_keys[j]]) * T[(i, j)] for i in range(m) for j in range(n))

    pe = {'Q1': e1, 'Q2': e2, 'Q3': e3}[primary]
    if augmecon and ranges is not None:
        sk = [k for k in ('Q1', 'Q2', 'Q3') if k != primary]
        se = [{'Q1': e1, 'Q2': e2, 'Q3': e3}[k] for k in sk]
        weights = [1.0, 0.1]
        tb = pl.lpSum((weights[k] / max(ranges[sk[k]], 1e-9)) * se[k] for k in range(len(se)))
        prob += pe + 1e-3 * tb
    else:
        prob += pe

    for j in range(n):
        prob += pl.lpSum(T[(i, j)] for i in range(m)) == 1, f'C2_{j}'

    for j in range(n):
        if roles[role_keys[j]].get('class_label') == 'operational':
            for i in range(m):
                if AGENTS[agent_keys[i]]['region_grid'] == 'RFCW':
                    prob += T[(i, j)] == 0, f'C3_{i}_{j}'

    for j in range(n):
        cap = role_max_latency(roles[role_keys[j]])
        for i in range(m):
            if AGENTS[agent_keys[i]]['latency_s'] > cap:
                prob += T[(i, j)] == 0, f'C4_{i}_{j}'

    if eps2 is not None and primary != 'Q2':
        prob += e2 <= eps2, 'eps2'
    if eps3 is not None and primary != 'Q3':
        prob += e3 <= eps3, 'eps3'

    return prob, T, e1, e2, e3, agent_keys


def solve(roles, role_keys, eps2=None, eps3=None, primary='Q1', augmecon=False, ranges=None, time_limit=15, gap_rel=0.01):
    prob, T, e1, e2, e3, agent_keys = build_lp(roles, role_keys, eps2, eps3, primary, augmecon, ranges)
    solver = pl.PULP_CBC_CMD(msg=False, timeLimit=time_limit, gapRel=gap_rel)
    status = prob.solve(solver)
    if pl.LpStatus[status] not in ('Optimal', 'Not Solved'):
        return None
    if any(T[(i, j)].value() is None for i in range(len(agent_keys)) for j in range(len(role_keys))):
        return None
    assignment = {role_keys[j]: agent_keys[i]
                  for j in range(len(role_keys))
                  for i in range(len(agent_keys))
                  if T[(i, j)].value() > 0.5}
    return {'Q1': pl.value(e1), 'Q2': pl.value(e2), 'Q3': pl.value(e3), 'assignment': assignment}


def lex_extreme(roles, role_keys, primary, second, third):
    s1 = solve(roles, role_keys, primary=primary)
    if not s1:
        return None
    p_opt = s1[primary]
    prob, T, e1, e2, e3, agent_keys = build_lp(roles, role_keys, primary=second)
    em = {'Q1': e1, 'Q2': e2, 'Q3': e3}
    prob += em[primary] <= p_opt + 1e-6
    solver = pl.PULP_CBC_CMD(msg=False, timeLimit=120)
    if pl.LpStatus[prob.solve(solver)] != 'Optimal':
        return s1
    s_opt = pl.value(em[second])
    prob, T, e1, e2, e3, agent_keys = build_lp(roles, role_keys, primary=third)
    em = {'Q1': e1, 'Q2': e2, 'Q3': e3}
    prob += em[primary] <= p_opt + 1e-6
    prob += em[second] <= s_opt + 1e-6
    if pl.LpStatus[prob.solve(solver)] != 'Optimal':
        return s1
    assignment = {role_keys[j]: agent_keys[i]
                  for j in range(len(role_keys))
                  for i in range(len(agent_keys))
                  if T[(i, j)].value() > 0.5}
    return {'Q1': pl.value(e1), 'Q2': pl.value(e2), 'Q3': pl.value(e3), 'assignment': assignment}


def find_extremes(roles, role_keys):
    plan = [('Q1', 'Q2', 'Q3'), ('Q2', 'Q1', 'Q3'), ('Q3', 'Q1', 'Q2')]
    return {p: lex_extreme(roles, role_keys, p, s, t) for p, s, t in plan}


def epsilon_grid(roles, role_keys, ext, k=20):
    Q1mn = ext['Q1']['Q1']; Q1mx = max(ext['Q2']['Q1'], ext['Q3']['Q1'])
    Q2mn = ext['Q2']['Q2']; Q2mx = max(ext['Q1']['Q2'], ext['Q3']['Q2'])
    Q3mn = ext['Q3']['Q3']; Q3mx = max(ext['Q1']['Q3'], ext['Q2']['Q3'])
    rng = {'Q1': max(Q1mx - Q1mn, 1e-9),
           'Q2': max(Q2mx - Q2mn, 1e-9),
           'Q3': max(Q3mx - Q3mn, 1e-9)}

    raw = []
    for k2 in range(k):
        for k3 in range(k):
            eps2 = Q2mn + (Q2mx - Q2mn) * k2 / (k - 1) if k > 1 else Q2mx
            eps3 = Q3mn + (Q3mx - Q3mn) * k3 / (k - 1) if k > 1 else Q3mx
            sol = solve(roles, role_keys, eps2=eps2, eps3=eps3, primary='Q1', augmecon=True, ranges=rng)
            if sol is not None:
                sol['eps2'] = eps2
                sol['eps3'] = eps3
                raw.append(sol)
    return raw


def filter_pareto(raw, dedup_decimals=2):
    seen = {}
    for c in raw:
        key = (round(c['Q1'], dedup_decimals), round(c['Q2'], dedup_decimals), round(c['Q3'], dedup_decimals))
        if key not in seen:
            seen[key] = c
    deduped = list(seen.values())
    nd = []
    for c in deduped:
        dominated = False
        for o in deduped:
            if o is c:
                continue
            if (o['Q1'] <= c['Q1'] and o['Q2'] <= c['Q2'] and o['Q3'] <= c['Q3'] and
                    (o['Q1'] < c['Q1'] or o['Q2'] < c['Q2'] or o['Q3'] < c['Q3'])):
                dominated = True
                break
        if not dominated:
            nd.append(c)
    return nd, len(deduped)


def compute(instance, k=20, write=True):
    roles = instance['role_details']
    role_keys = instance['role_keys']
    t0 = time.perf_counter()
    ext = find_extremes(roles, role_keys)
    t_ext = time.perf_counter() - t0

    t1 = time.perf_counter()
    raw = epsilon_grid(roles, role_keys, ext, k=k)
    t_grid = time.perf_counter() - t1

    nd, dedup_count = filter_pareto(raw)

    out = {
        'k_grid': k,
        'time_extremes_s': round(t_ext, 2),
        'time_grid_s': round(t_grid, 2),
        'extremes': ext,
        'pareto_raw_count': len(raw),
        'pareto_unique_count': dedup_count,
        'pareto_nd_count': len(nd),
        'pareto_front': nd,
    }
    if write:
        RESULTS_DIR.mkdir(exist_ok=True)
        path = RESULTS_DIR / f'pareto_k{k}.json'
        path.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=str), encoding='utf-8')
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--k', type=int, default=20)
    args = ap.parse_args()
    instance = json.loads((RESULTS_DIR / 'instance_toronto.json').read_text(encoding='utf-8'))
    out = compute(instance, k=args.k)
    print(f'pareto k={args.k} nd={out["pareto_nd_count"]} time_grid_s={out["time_grid_s"]}')
