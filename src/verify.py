import json
from pathlib import Path

from .parameters import (AGENTS, PUE, GRID_CO2, KWH_PER_GB_MONTH,
                         EMBODIED_KG_PER_GB, LIFETIME_MONTHS, TRANSFER_OUT)
from .objectives import q1_cost, q2_latency, q3_co2

RESULTS_DIR = Path(__file__).parent.parent / 'results'

DEFAULT_SAMPLE_ROLES = [
    'Toronto_Police_Services__op_live',
    'Toronto_Public_Library__op_recent',
    'Lobbyist_Registrar__op_archive',
    'Transportation_Services__open',
]


def q1_manual(agent_key, role):
    a = AGENTS[agent_key]
    sz = role['size_gb']
    reads = role['reads_gb_month']
    transfer = a.get('transfer_override', TRANSFER_OUT[a['provider']])
    return sz * a['price'] + reads * (a['retrieval'] + transfer)


def q2_manual(agent_key, role):
    return role['reads_gb_month'] * AGENTS[agent_key]['latency_s']


def q3_manual(agent_key, role):
    a = AGENTS[agent_key]
    op = PUE[a['provider']] * KWH_PER_GB_MONTH[a['media']] * GRID_CO2[a['region_grid']]
    emb = EMBODIED_KG_PER_GB[a['media']] / LIFETIME_MONTHS[a['media']]
    return role['size_gb'] * (op + emb)


def run(sample_keys=None, instance=None, write=True):
    if instance is None:
        instance = json.loads((RESULTS_DIR / 'instance_toronto.json').read_text(encoding='utf-8'))
    roles = instance['role_details']
    keys = sample_keys or [k for k in DEFAULT_SAMPLE_ROLES if k in roles]
    if not keys:
        keys = list(roles.keys())[:4]

    max_diff = {'Q1': 0.0, 'Q2': 0.0, 'Q3': 0.0}
    cells = []
    for rk in keys:
        role = roles[rk]
        for ak in AGENTS:
            qc = (q1_cost(ak, role), q2_latency(ak, role), q3_co2(ak, role))
            qm = (q1_manual(ak, role), q2_manual(ak, role), q3_manual(ak, role))
            for label, c, m in zip(('Q1', 'Q2', 'Q3'), qc, qm):
                d = abs(c - m) / max(abs(m), 1e-30)
                if d > max_diff[label]:
                    max_diff[label] = d
            cells.append({'role': rk, 'agent': ak, 'Q_code': qc, 'Q_manual': qm})

    out = {
        'sample_roles': keys,
        'cells_total': len(cells),
        'max_relative_diff': max_diff,
        'machine_precision_pass': all(v < 1e-12 for v in max_diff.values()),
    }
    if write:
        path = RESULTS_DIR / 'verification.json'
        path.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=str), encoding='utf-8')
    return out


if __name__ == '__main__':
    out = run()
    print(f'cells={out["cells_total"]} max_diff={max(out["max_relative_diff"].values()):.2e} pass={out["machine_precision_pass"]}')
