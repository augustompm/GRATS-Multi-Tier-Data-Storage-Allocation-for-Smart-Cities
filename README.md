# GRATS

Source code and data for GRATS (Multi-Tier Data Storage Allocation for Smart Cities) on the Toronto canonical instance: 16 agents across three jurisdictions, 184 roles from 46 owner divisions (Open class plus Operational class with Live, Recent, Archive sub-tiers), three objectives (cost, volume-weighted latency, amortized embodied plus operational CO2), and four hard constraints including Cloud Data Residency CIMS-G017.

The pipeline builds the instance from a public CKAN snapshot of Open Data Toronto, verifies the objective functions cell by cell, computes the Pareto frontier via epsilon-constraint with AUGMECON in CBC, applies post-Pareto MCDA via TOPSIS and canonical VIKOR with C1/C2 acceptance rules and a Q1 cost-efficiency tiebreaker, runs a sensitivity sweep, and produces the figure used in the paper.

Run order from the project root: `python -m src.pipeline` reproduces all numeric results and writes JSON outputs to `results/`. Individual stages can be invoked as `python -m src.<module>`. Python 3.13, PuLP 2.7, CBC 2.10. See `requirements.txt` for the full list.

Inputs in `data/` are the CKAN catalog snapshot and the parsed Toronto Operating Budget per program. Outputs in `results/` are JSON files; the figure is written to `figures/`.
