import json
import math
from pathlib import Path

RESULTS_DIR = Path(__file__).parent.parent / 'results'

PROFILES = {
    'P1_Well_Run_City':    [0.60, 0.25, 0.15],
    'P2_Service_Delivery': [0.20, 0.60, 0.20],
    'P3_Equity_Inclusion': [0.30, 0.50, 0.20],
    'P4_Climate_Officer':  [0.20, 0.20, 0.60],
}


def log_linear_normalize(pareto):
    Q = [[math.log10(max(p['Q1'], 1e-12)),
          math.log10(max(p['Q2'], 1e-12)),
          math.log10(max(p['Q3'], 1e-12))] for p in pareto]
    fmin = [min(q[k] for q in Q) for k in range(3)]
    fmax = [max(q[k] for q in Q) for k in range(3)]
    return Q, fmin, fmax


def topsis(pareto, w):
    Q, fmin, fmax = log_linear_normalize(pareto)
    Qn = [[(q[k] - fmin[k]) / max(fmax[k] - fmin[k], 1e-9) * w[k] for k in range(3)] for q in Q]
    ip = [min(qn[k] for qn in Qn) for k in range(3)]
    ina = [max(qn[k] for qn in Qn) for k in range(3)]
    closeness = []
    for qn in Qn:
        sp = math.sqrt(sum((qn[k] - ip[k]) ** 2 for k in range(3)))
        sn = math.sqrt(sum((qn[k] - ina[k]) ** 2 for k in range(3)))
        closeness.append(sn / max(sp + sn, 1e-9))
    return sorted(range(len(pareto)), key=lambda i: -closeness[i])


def vikor_canonical(pareto, w, v=0.5):
    Q, fmin, fmax = log_linear_normalize(pareto)
    n = len(Q)
    S, R = [], []
    for q in Q:
        gaps = [w[k] * (q[k] - fmin[k]) / max(fmax[k] - fmin[k], 1e-9) for k in range(3)]
        S.append(sum(gaps))
        R.append(max(gaps))
    Smin, Smax = min(S), max(S)
    Rmin, Rmax = min(R), max(R)
    Qv = [v * (S[i] - Smin) / max(Smax - Smin, 1e-9) +
          (1 - v) * (R[i] - Rmin) / max(Rmax - Rmin, 1e-9) for i in range(n)]
    order = sorted(range(n), key=lambda i: Qv[i])
    DQ = 1.0 / max(n - 1, 1)
    a1 = order[0]
    a2 = order[1] if n > 1 else order[0]
    eps = 1e-9
    c1_pass = (Qv[a2] - Qv[a1]) >= DQ
    c2_pass = (abs(S[a1] - Smin) < eps) or (abs(R[a1] - Rmin) < eps)

    if not c1_pass:
        compromise = [a1]
        for i in range(1, n):
            if Qv[order[i]] - Qv[a1] < DQ:
                compromise.append(order[i])
            else:
                break
    elif not c2_pass:
        compromise = [a1, a2]
    else:
        compromise = [a1]

    return {
        'order': order,
        'Qv': Qv,
        'S': S,
        'R': R,
        'c1_pass': c1_pass,
        'c2_pass': c2_pass,
        'compromise_set': compromise,
    }


def q1_tiebreaker(pareto, indices):
    return min(indices, key=lambda i: pareto[i]['Q1'])


def evaluate_profiles(pareto, profiles=PROFILES):
    out = {}
    for name, w in profiles.items():
        t_order = topsis(pareto, w)
        topsis_top1 = t_order[0]
        v = vikor_canonical(pareto, w)
        cset = v['compromise_set']
        final_pick = q1_tiebreaker(pareto, cset) if len(cset) > 1 else cset[0]
        out[name] = {
            'weights': w,
            'topsis_top1_idx': topsis_top1,
            'topsis_top1_Q': {k: pareto[topsis_top1][k] for k in ('Q1', 'Q2', 'Q3')},
            'vikor_compromise_set': cset,
            'vikor_c1_pass': v['c1_pass'],
            'vikor_c2_pass': v['c2_pass'],
            'vikor_pick_idx': final_pick,
            'vikor_pick_Q': {k: pareto[final_pick][k] for k in ('Q1', 'Q2', 'Q3')},
            'topsis_in_compromise_set': topsis_top1 in cset,
        }
    return out


def run(pareto_file=None, write=True):
    if pareto_file is None:
        pareto_file = RESULTS_DIR / 'pareto_k20.json'
    data = json.loads(Path(pareto_file).read_text(encoding='utf-8'))
    pareto = data['pareto_front']
    results = evaluate_profiles(pareto)
    agreement_count = sum(1 for r in results.values() if r['topsis_in_compromise_set'])
    result = {
        'pareto_n': len(pareto),
        'profiles': PROFILES,
        'results': results,
        'agreement_count': agreement_count,
        'agreement_pct': 100.0 * agreement_count / max(len(results), 1),
    }
    if write:
        path = RESULTS_DIR / 'mcda.json'
        path.write_text(json.dumps(result, indent=2, ensure_ascii=False, default=str), encoding='utf-8')
    return result


if __name__ == '__main__':
    out = run()
    for name, r in out['results'].items():
        c1 = 'pass' if r['vikor_c1_pass'] else 'fail'
        c2 = 'pass' if r['vikor_c2_pass'] else 'fail'
        cs = len(r['vikor_compromise_set'])
        q1 = r['vikor_pick_Q']['Q1']
        q3 = r['vikor_pick_Q']['Q3']
        print(f'{name} c1={c1} c2={c2} |Ac|={cs} pick=(Q1={q1:.0f}, Q3={q3:.0f})')
