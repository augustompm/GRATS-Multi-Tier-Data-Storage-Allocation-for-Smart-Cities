"""Pareto frontier figure: three pairwise projections with in-cluster VIKOR picks."""

import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

RESULTS_DIR = Path(__file__).parent.parent / 'results'
FIGURES_DIR = Path(__file__).parent.parent / 'figures'

IN_CLUSTER_PROFILES = {
    'P1_Well_Run_City':   {'marker': 'D', 'color': 'red',   'label': 'P1 Well-Run'},
    'P4_Climate_Officer': {'marker': 's', 'color': 'green', 'label': 'P4 Climate'},
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

    picks = []
    for name, style in IN_CLUSTER_PROFILES.items():
        idx = mcda[name]['vikor_pick_idx']
        p = pareto[idx]
        picks.append((p['Q1'] / 1000, p['Q2'] / 1e6, p['Q3'], style))

    q2_low = max(np.percentile(Q2, 5), 1.0)
    q2_high = max(Q2) * 1.5
    q1_high = max(p[0] for p in picks) * 1.8

    fig, axes = plt.subplots(1, 3, figsize=(15, 5.0))

    sc0 = axes[0].scatter(Q1, Q2, c=Q3, cmap='viridis', s=30, alpha=0.75, edgecolors='gray', linewidths=0.3)
    axes[0].set_xscale('log'); axes[0].set_yscale('log')
    axes[0].set_xlim(min(Q1) * 0.85, q1_high)
    axes[0].set_ylim(q2_low * 0.5, q2_high)
    axes[0].set_xlabel(r'$Q_1$ cost (k\$/mo, log)')
    axes[0].set_ylabel(r'$Q_2$ latency (M$\cdot$s$\cdot$GB/mo, log)')
    axes[0].set_title(r'(a) $Q_1$ vs $Q_2$ (color = $Q_3$)')
    axes[0].grid(alpha=0.3, which='both')
    plt.colorbar(sc0, ax=axes[0], shrink=0.8, pad=0.02).set_label(r'$Q_3$ (kg/mo)', fontsize=8)

    sc1 = axes[1].scatter(Q1, Q3, c=np.log10(Q2 + 1e-3), cmap='plasma', s=30, alpha=0.75, edgecolors='gray', linewidths=0.3)
    axes[1].set_xscale('log'); axes[1].set_yscale('log')
    axes[1].set_xlim(min(Q1) * 0.85, q1_high)
    axes[1].set_xlabel(r'$Q_1$ cost (k\$/mo, log)')
    axes[1].set_ylabel(r'$Q_3$ CO$_2$ (kg/mo, log)')
    axes[1].set_title(r'(b) $Q_1$ vs $Q_3$ (color = $\log Q_2$)')
    axes[1].grid(alpha=0.3, which='both')
    plt.colorbar(sc1, ax=axes[1], shrink=0.8, pad=0.02).set_label(r'$\log_{10}(Q_2)$', fontsize=8)

    sc2 = axes[2].scatter(Q2, Q3, c=Q1, cmap='cividis', s=30, alpha=0.75, edgecolors='gray', linewidths=0.3)
    axes[2].set_xscale('log'); axes[2].set_yscale('log')
    axes[2].set_xlim(q2_low * 0.5, q2_high)
    axes[2].set_xlabel(r'$Q_2$ latency (M$\cdot$s$\cdot$GB/mo, log)')
    axes[2].set_ylabel(r'$Q_3$ CO$_2$ (kg/mo, log)')
    axes[2].set_title(r'(c) $Q_2$ vs $Q_3$ (color = $Q_1$)')
    axes[2].grid(alpha=0.3, which='both')
    plt.colorbar(sc2, ax=axes[2], shrink=0.8, pad=0.02).set_label(r'$Q_1$ (k\$/mo)', fontsize=8)

    for q1, q2, q3, st in picks:
        axes[0].scatter([q1], [q2], c=st['color'], s=200, marker=st['marker'],
                        edgecolors='black', linewidths=1.3, label=st['label'], zorder=6)
        axes[1].scatter([q1], [q3], c=st['color'], s=200, marker=st['marker'],
                        edgecolors='black', linewidths=1.3, zorder=6)
        axes[2].scatter([q2], [q3], c=st['color'], s=200, marker=st['marker'],
                        edgecolors='black', linewidths=1.3, zorder=6)

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='lower center', bbox_to_anchor=(0.5, -0.02),
               ncol=2, fontsize=10, frameon=True)
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
