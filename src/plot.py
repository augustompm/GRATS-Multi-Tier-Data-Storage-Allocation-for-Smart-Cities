"""Pareto frontier figure: three pairwise projections of the main cluster (lex extremes excluded)."""

import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


RESULTS_DIR = Path(__file__).parent.parent / 'results'
FIGURES_DIR = Path(__file__).parent.parent / 'figures'


def render(pareto_file=None, output='fig1_pareto_3d.pdf'):
    if pareto_file is None:
        pareto_file = RESULTS_DIR / 'pareto_k20.json'
    pareto = json.loads(Path(pareto_file).read_text(encoding='utf-8'))['pareto_front']

    q1_min = min(p['Q1'] for p in pareto)
    q2_min = min(p['Q2'] for p in pareto)
    q3_min = min(p['Q3'] for p in pareto)
    main = [p for p in pareto if p['Q1'] != q1_min and p['Q2'] != q2_min and p['Q3'] != q3_min]

    Q1 = np.array([p['Q1'] for p in main]) / 1000
    Q2 = np.array([p['Q2'] for p in main]) / 1e6
    Q3 = np.array([p['Q3'] for p in main])

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.6))

    sc0 = axes[0].scatter(Q1, Q2, c=Q3, cmap='viridis', s=30, alpha=0.8, edgecolors='gray', linewidths=0.3)
    axes[0].set_xscale('log'); axes[0].set_yscale('log')
    axes[0].set_xlabel(r'$Q_1$ cost (k\$/mo, log)')
    axes[0].set_ylabel(r'$Q_2$ latency (M$\cdot$s$\cdot$GB/mo, log)')
    axes[0].set_title(r'(a) $Q_1$ vs $Q_2$ (color = $Q_3$)')
    axes[0].grid(alpha=0.3, which='both')
    plt.colorbar(sc0, ax=axes[0], shrink=0.85, pad=0.02).set_label(r'$Q_3$ (kg/mo)', fontsize=9)

    sc1 = axes[1].scatter(Q1, Q3, c=np.log10(Q2 + 1e-3), cmap='plasma', s=30, alpha=0.8, edgecolors='gray', linewidths=0.3)
    axes[1].set_xscale('log'); axes[1].set_yscale('log')
    axes[1].set_xlabel(r'$Q_1$ cost (k\$/mo, log)')
    axes[1].set_ylabel(r'$Q_3$ CO$_2$ (kg/mo, log)')
    axes[1].set_title(r'(b) $Q_1$ vs $Q_3$ (color = $\log Q_2$)')
    axes[1].grid(alpha=0.3, which='both')
    plt.colorbar(sc1, ax=axes[1], shrink=0.85, pad=0.02).set_label(r'$\log_{10}(Q_2)$', fontsize=9)

    sc2 = axes[2].scatter(Q2, Q3, c=Q1, cmap='cividis', s=30, alpha=0.8, edgecolors='gray', linewidths=0.3)
    axes[2].set_xscale('log'); axes[2].set_yscale('log')
    axes[2].set_xlabel(r'$Q_2$ latency (M$\cdot$s$\cdot$GB/mo, log)')
    axes[2].set_ylabel(r'$Q_3$ CO$_2$ (kg/mo, log)')
    axes[2].set_title(r'(c) $Q_2$ vs $Q_3$ (color = $Q_1$)')
    axes[2].grid(alpha=0.3, which='both')
    plt.colorbar(sc2, ax=axes[2], shrink=0.85, pad=0.02).set_label(r'$Q_1$ (k\$/mo)', fontsize=9)

    plt.tight_layout()

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
