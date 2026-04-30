"""Build the Toronto canonical instance: 184 roles from CKAN catalog plus budget-scaled volumes."""

import json
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

from .parameters import (
    ALPHA, BETA, C4_MAX_LATENCY_S, SUB_TIERS,
    TPS_OPERATIONAL_VOLUME_PB, TPS_PROGRAM_NAME,
)

DATA_DIR = Path(__file__).parent.parent / 'data'
RESULTS_DIR = Path(__file__).parent.parent / 'results'

OPS_BY_REFRESH = {
    'Real-time': 1000.0, 'Daily': 100.0, 'Weekly': 30.0, 'Monthly': 10.0,
    'Quarterly': 3.0, 'Semi-annually': 2.0, 'Annually': 1.0,
    'As available': 0.5, 'Will not be Refreshed': 0.1,
}
AVG_OPEN_RESOURCE_GB = 4.14e-4


def normalize_division_name(name):
    return name.replace(' ', '_').replace("'", '').replace('&', 'and').replace(',', '')


def load_catalog():
    catalog = json.loads((DATA_DIR / 'ckan_catalog.json').read_text(encoding='utf-8'))
    return catalog['datasets']


def load_intensity_map():
    return json.loads((DATA_DIR / 'intensity_multipliers.json').read_text(encoding='utf-8'))


def load_budget_salaries():
    path = DATA_DIR / 'toronto_operating_budget_2025.json'
    if path.exists():
        return json.loads(path.read_text(encoding='utf-8'))
    xlsx = DATA_DIR / 'toronto_operating_budget_2025.xlsx'
    df = pd.read_excel(xlsx)
    df = df[df['Expense/Revenue'].str.contains('Expense', na=False)]
    sal = df[df['Category Name'].str.contains('Salar|Benefit', case=False, na=False)]
    salaries = sal.groupby('Program')['2025'].sum().to_dict()
    path.write_text(json.dumps(salaries, indent=2), encoding='utf-8')
    return salaries


def aggregate_by_division(datasets):
    by_division = defaultdict(list)
    for ds in datasets:
        div = ds.get('owner_division')
        if div:
            by_division[div].append(ds)
    return by_division


def division_stats(datasets_in_div):
    size_bytes = 0
    size_known = size_unknown = 0
    ops_total = 0.0
    topic_counter = Counter()
    civic_counter = Counter()
    for ds in datasets_in_div:
        for r in ds.get('resources', []):
            sz = r.get('size')
            if sz and sz > 0:
                size_bytes += sz
                size_known += 1
            else:
                size_unknown += 1
        rr = ds.get('refresh_rate')
        ops_total += OPS_BY_REFRESH.get(rr, 0.5)
        for t in ds.get('topics') or []:
            topic_counter[t] += 1
        for ci in ds.get('civic_issues') or []:
            civic_counter[ci] += 1
    if size_known > 0 and size_unknown > 0:
        avg = size_bytes / size_known
        size_bytes += avg * size_unknown
    size_gb = max(size_bytes / (1024 ** 3), 1e-6)
    topic_dom = topic_counter.most_common(1)[0][0] if topic_counter else None
    civic_dom = civic_counter.most_common(1)[0][0] if civic_counter else None
    return size_gb, ops_total, topic_dom, civic_dom


def operational_volumes(by_division, intensity, salaries, ckan_to_program):
    tps_salary = salaries.get(TPS_PROGRAM_NAME, 1)
    volumes = {}
    for div in by_division:
        program = ckan_to_program.get(div)
        salary = salaries.get(program, tps_salary * 0.05) if program else tps_salary * 0.05
        mult = intensity.get(div, 0.05)
        volumes[div] = TPS_OPERATIONAL_VOLUME_PB * 1e6 * (salary / tps_salary) * mult
    return volumes


def build_roles(by_division, op_volumes):
    roles = {}
    role_keys = []
    for division in sorted(by_division.keys(), key=lambda d: -len(by_division[d])):
        dsl = by_division[division]
        slug = normalize_division_name(division)
        size_open, ops_total, topic_dom, civic_dom = division_stats(dsl)

        key_open = f'{slug}__open'
        roles[key_open] = {
            'parent': division, 'division': division,
            'class_label': 'open', 'sub_tier': None,
            'size_gb': size_open,
            'reads_gb_month': ops_total * AVG_OPEN_RESOURCE_GB,
            'num_datasets': len(dsl),
            'topic_dominant': topic_dom, 'civic_issue_dominant': civic_dom,
            'c4_max_latency_s': float('inf'),
        }
        role_keys.append(key_open)

        total_op_gb = op_volumes.get(division, size_open * 100.0)
        for st in SUB_TIERS:
            size_st = total_op_gb * ALPHA[st]
            reads_st = size_st * BETA[st]
            key = f'{slug}__op_{st.lower()}'
            roles[key] = {
                'parent': division, 'division': division,
                'class_label': 'operational', 'sub_tier': st,
                'size_gb': size_st, 'reads_gb_month': reads_st,
                'alpha': ALPHA[st], 'beta': BETA[st],
                'total_op_gb': total_op_gb,
                'topic_dominant': topic_dom, 'civic_issue_dominant': civic_dom,
                'c4_max_latency_s': C4_MAX_LATENCY_S[st],
            }
            role_keys.append(key)
    return roles, role_keys


def build_instance(write=True):
    datasets = load_catalog()
    by_division = aggregate_by_division(datasets)
    intensity = load_intensity_map()
    salaries = load_budget_salaries()
    ckan_to_program = intensity['_ckan_to_program']
    multipliers = {k: v for k, v in intensity.items() if not k.startswith('_')}
    op_volumes = operational_volumes(by_division, multipliers, salaries, ckan_to_program)
    roles, role_keys = build_roles(by_division, op_volumes)

    out = {
        'role_keys': role_keys,
        'role_details': roles,
        'alpha': ALPHA, 'beta': BETA,
        'c4_max_latency_s': {k: (None if v == float('inf') else v) for k, v in C4_MAX_LATENCY_S.items()},
    }
    if write:
        RESULTS_DIR.mkdir(exist_ok=True)
        path = RESULTS_DIR / 'instance_toronto.json'
        path.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=str), encoding='utf-8')
    return out


if __name__ == '__main__':
    inst = build_instance()
    n_open = sum(1 for v in inst['role_details'].values() if v['class_label'] == 'open')
    n_op = sum(1 for v in inst['role_details'].values() if v['class_label'] == 'operational')
    print(f'roles open={n_open} operational={n_op}')
