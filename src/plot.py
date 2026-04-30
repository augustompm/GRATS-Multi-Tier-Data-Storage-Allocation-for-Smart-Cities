"""Pareto frontier figure: three pairwise projections plus VIKOR canonical picks."""

import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

RESULTS_DIR = Path(__file__).parent.parent / 'results'
FIGURES_DIR = Path(__file__).parent.parent / 'figures'

PROFILE_STYLE = {
    'P1_Well_Run_City':    {'marker': 'D', 'color': 'red',   'label': 'P1 Well-Run'},
    'P2_Service_Delivery': {'marker': '*', 'color': 'blue',  'label': 'P2/P3'},
    'P3_Equity_Inclusion': {'marker': '*', 'color': 'blue',  'label': None},
    'P4_Climate_Officer':  {'marker': 's', 'color': 'green', 'label': 'P4 Climate'},
}


def render(pareto_file=None, mcda_file=None, output='fig1_pareto_3d.pdf'):
    if pareto_file is None:
        pareto_file = RESULTS_DIR / 'pareto_k20.json'
    if mcda_file is None:
        mcda_file = RESULTS_DIR / 'mcda.json'
    pareto = json.loads(Path(pareto_file).read_text(encoding='utf-8'))['pareto_front']
    mcda = json.loads(Path(mcda_file).read_text(encoding='utf-8'))['results']

    Q1 = np.array([p['Q1'] for p in pareto]) / 1000
    Q2 = np.array([p['Q2'] for p in pareto]) / 1e6
    Q3 = np.array([p['Q3'] for p in pareto])

    ext_q1 = min(pareto, key=lambda p: p['Q1'])
    ext_q2 = min(pareto, key=lambda p: p['Q2'])
    ext_q3 = min(pareto, key=lambda p: p['Q3'])
    eQ1 = np.array([e['Q1'] for e in (ext_q1, ext_q2, ext_q3)]) / 1000
    eQ2 = np.array([e['Q2'] for e in (ext_q1, ext_q2, ext_q3)]) / 1e6
    eQ3 = np.array([e['Q3'] for e in (ext_q1, ext_q2, ext_q3)])

    picks = {}
    for name, r in mcda.items():
        idx = r['vikor_pick_idx']
        picks[name] = (pareto[idx]['Q1'] / 1000, pareto[idx]['Q2'] / 1e6, pareto[idx]['Q3'])

    fig, axes = plt.subplots(1, 3, figsize=(15, 5.2))

    sc0 = axes[0].scatter(Q1, Q2, c=Q3, cmap='viridis', s=28, alpha=0.7, edgecolors='gray', linewidths=0.3)
    axes[0].scatter(eQ1, eQ2, s=240, facecolors='none', edgecolors='red', linewidths=2.2, label='lex extremes', zorder=4)
    axes[0].set_xscale('log'); axes[0].set_yscale('log')
    axes[0].set_xlabel(r'$Q_1$ cost (k\$/mo, log)')
    axes[0].set_ylabel(r'$Q_2$ latency (M$\cdot$s$\cdot$GB/mo, log)')
    axes[0].set_title(r'(a) $Q_1$ vs $Q_2$ (color = $Q_3$)')
    axes[0].grid(alpha=0.3, which='both')
    plt.colorbar(sc0, ax=axes[0], shrink=0.8, pad=0.02).set_label(r'$Q_3$ (kg/mo)', fontsize=8)

    sc1 = axes[1].scatter(Q1, Q3, c=np.log10(Q2 + 1e-3), cmap='plasma', s=28, alpha=0.7, edgecolors='gray', linewidths=0.3)
    axes[1].scatter(eQ1, eQ3, s=240, facecolors='none', edgecolors='red', linewidths=2.2, zorder=4)
    axes[1].set_xscale('log'); axes[1].set_yscale('log')
    axes[1].set_xlabel(r'$Q_1$ cost (k\$/mo, log)')
    axes[1].set_ylabel(r'$Q_3$ CO$_2$ (kg/mo, log)')
    axes[1].set_title(r'(b) $Q_1$ vs $Q_3$ (color = $\log Q_2$)')
    axes[1].grid(alpha=0.3, which='both')
    plt.colorbar(sc1, ax=axes[1], shrink=0.8, pad=0.02).set_label(r'$\log_{10}(Q_2)$', fontsize=8)

    sc2 = axes[2].scatter(Q2, Q3, c=Q1, cmap='cividis', s=28, alpha=0.7, edgecolors='gray', linewidths=0.3)
    axes[2].scatter(eQ2, eQ3, s=240, facecolors='none', edgecolors='red', linewidths=2.2, zorder=4)
    axes[2].set_xscale('log'); axes[2].set_yscale('log')
    axes[2].set_xlabel(r'$Q_2$ latency (M$\cdot$s$\cdot$GB/mo, log)')
    axes[2].set_ylabel(r'$Q_3$ CO$_2$ (kg/mo, log)')
    axes[2].set_title(r'(c) $Q_2$ vs $Q_3$ (color = $Q_1$)')
    axes[2].grid(alpha=0.3, which='both')
    plt.colorbar(sc2, ax=axes[2], shrink=0.8, pad=0.02).set_label(r'$Q_1$ (k\$/mo)', fontsize=8)

    for name, (q1, q2, q3) in picks.items():
        st = PROFILE_STYLE[name]
        axes[0].scatter([q1], [q2], c=st['color'], s=200, marker=st['marker'],
                        edgecolors='black', linewidths=1.3, label=st['label'], zorder=6)
        axes[1].scatter([q1], [q3], c=st['color'], s=200, marker=st['marker'],
                        edgecolors='black', linewidths=1.3, zorder=6)
        axes[2].scatter([q2], [q3], c=st['color'], s=200, marker=st['marker'],
                        edgecolors='black', linewidths=1.3, zorder=6)

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='lower center', bbox_to_anchor=(0.5, -0.02),
               ncol=4, fontsize=10, frameon=True)
    plt.tight_layout(rect=(0, 0.05, 1, 1))

    FIGURES_DIR.mkdir(exist_ok=True)
    out_pdf = FIGURES_DIR / output
    out_png = FIGURES_DIR / output.replace('.pdf', '.png')
    fig.savefig(out_pdf, dpi=150, bbox_inches='tight')
    fig.savefig(out_png, dpi=150, bbox_inches='tight')
    plt.close(fig)
    return out_pdf


if __name__ == '__main__':
    p = render()
    print(f'figure={p.name}')
