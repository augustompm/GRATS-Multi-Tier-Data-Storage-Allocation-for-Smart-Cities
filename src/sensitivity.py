"""Sensitivity sweep over alpha, beta, C4 caps, TPS anchor, intensity scale."""

import copy
import json
import time
from pathlib import Path

from .parameters import ALPHA, BETA, C4_MAX_LATENCY_S
from .pareto import compute as compute_pareto
from .mcda import evaluate_profiles, PROFILES

RESULTS_DIR = Path(__file__).parent.parent / 'results'

PERTURBATIONS = [
    ('baseline',         {}),
    ('alpha_live_low',   {'alpha': {'Live': 0.025, 'Recent': 0.18, 'Archive': 0.795}}),
    ('alpha_live_high',  {'alpha': {'Live': 0.10, 'Recent': 0.18, 'Archive': 0.72}}),
    ('alpha_rec_low',    {'alpha': {'Live': 0.05, 'Recent': 0.09, 'Archive': 0.86}}),
    ('alpha_rec_high',   {'alpha': {'Live': 0.05, 'Recent': 0.36, 'Archive': 0.59}}),
    ('beta_live_low',    {'beta': {'Live': 1.5, 'Recent': 0.10, 'Archive': 0.001}}),
    ('beta_live_high',   {'beta': {'Live': 6.0, 'Recent': 0.10, 'Archive': 0.001}}),
    ('beta_rec_low',     {'beta': {'Live': 3.0, 'Recent': 0.05, 'Archive': 0.001}}),
    ('beta_rec_high',    {'beta': {'Live': 3.0, 'Recent': 0.20, 'Archive': 0.001}}),
    ('c4_live_30s',      {'c4': {'Live': 30.0, 'Recent': 3600.0, 'Archive': float('inf')}}),
    ('c4_live_120s',     {'c4': {'Live': 120.0, 'Recent': 3600.0, 'Archive': float('inf')}}),
    ('c4_rec_1800s',     {'c4': {'Live': 60.0, 'Recent': 1800.0, 'Archive': float('inf')}}),
    ('c4_rec_7200s',     {'c4': {'Live': 60.0, 'Recent': 7200.0, 'Archive': float('inf')}}),
    ('tps_low',          {'tps_pb': 2.5}),
    ('tps_high',         {'tps_pb': 10.0}),
    ('tps_extreme',      {'tps_pb': 15.0}),
    ('intensity_half',   {'intensity_scale': 0.5}),
    ('intensity_double', {'intensity_scale': 2.0}),
]


def patch_instance(baseline_instance, alpha=None, beta=None, c4=None, tps_pb=None, intensity_scale=None):
    alpha = alpha or ALPHA
    beta = beta or BETA
    c4 = c4 or C4_MAX_LATENCY_S
    tps_anchor_gb = (tps_pb or 5.0) * 1e6
    iscale = intensity_scale if intensity_scale is not None else 1.0

    roles = copy.deepcopy(baseline_instance['role_details'])
    out = {}
    for k, v in roles.items():
        v = dict(v)
        if v.get('class_label') != 'operational':
            v['c4_max_latency_s'] = float('inf')
            out[k] = v
            continue
        sub = v.get('sub_tier', 'Archive')
        if sub not in alpha:
            sub = 'Archive'
        baseline_total = v['size_gb'] / ALPHA[sub]
        if v['division'] == 'Toronto Police Services':
            new_total = tps_anchor_gb
        else:
            new_total = baseline_total * iscale
        new_size = new_total * alpha[sub]
        v['size_gb'] = new_size
        v['reads_gb_month'] = new_size * beta[sub]
        v['alpha'] = alpha[sub]
        v['beta'] = beta[sub]
        v['c4_max_latency_s'] = c4[sub]
        out[k] = v
    return {'role_keys': baseline_instance['role_keys'], 'role_details': out}


def run(baseline_instance=None, k=20, write=True):
    if baseline_instance is None:
        baseline_instance = json.loads((RESULTS_DIR / 'instance_toronto.json').read_text(encoding='utf-8'))

    baseline_pareto = compute_pareto(baseline_instance, k=k, write=False)
    base_card = baseline_pareto['pareto_nd_count']
    base_mcda = evaluate_profiles(baseline_pareto['pareto_front'])
    base_picks = {p: r['vikor_pick_idx'] for p, r in base_mcda.items()}

    runs = []
    for name, params in PERTURBATIONS:
        t0 = time.perf_counter()
        instance = patch_instance(baseline_instance, **params)
        pareto = compute_pareto(instance, k=k, write=False)
        mcda = evaluate_profiles(pareto['pareto_front'])
        picks = {p: r['vikor_pick_idx'] for p, r in mcda.items()}
        nd = pareto['pareto_nd_count']
        delta = (nd - base_card) / max(base_card, 1) * 100
        within_v1 = abs(delta) <= 30.0
        winners_shifted = sum(1 for p in PROFILES if picks[p] != base_picks[p])
        runs.append({
            'name': name,
            'cardinality': nd,
            'cardinality_delta_pct': round(delta, 2),
            'within_v1_30pct': within_v1,
            'mcda_winners_shifted': winners_shifted,
            'time_s': round(time.perf_counter() - t0, 2),
        })

    out = {
        'baseline_cardinality': base_card,
        'k_grid': k,
        'runs': runs,
        'v1_pass_count': sum(1 for r in runs if r['within_v1_30pct']),
    }
    if write:
        path = RESULTS_DIR / 'sensitivity.json'
        path.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=str), encoding='utf-8')
    return out


if __name__ == '__main__':
    out = run()
    print(f'baseline_card={out["baseline_cardinality"]} v1_pass={out["v1_pass_count"]}/{len(out["runs"])}')
