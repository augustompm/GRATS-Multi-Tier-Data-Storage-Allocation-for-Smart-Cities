from . import instance, verify, pareto, mcda, baselines, sensitivity


def main(k=40, run_sensitivity=True):
    print('stage=instance')
    inst = instance.build_instance(write=True)

    print('stage=verify')
    v = verify.run(instance=inst, write=True)
    if not v['machine_precision_pass']:
        raise RuntimeError('verification failed')

    print('stage=pareto')
    par = pareto.compute(inst, k=k, write=True)

    print('stage=mcda')
    mc = mcda.run(pareto_file=mcda.RESULTS_DIR / f'pareto_k{k}.json', write=True)

    print('stage=baselines')
    bl = baselines.run(instance=inst, pareto=par, write=True)

    if run_sensitivity:
        print('stage=sensitivity')
        sn = sensitivity.run(baseline_instance=inst, k=k, write=True)
    else:
        sn = None

    n_open = sum(1 for v in inst['role_details'].values() if v['class_label'] == 'open')
    n_op = sum(1 for v in inst['role_details'].values() if v['class_label'] == 'operational')
    print(f'roles open={n_open} operational={n_op} pareto_nd={par["pareto_nd_count"]} '
          f'mcda_agreement={mc["agreement_count"]}/4')


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--k', type=int, default=40)
    ap.add_argument('--no-sensitivity', action='store_true')
    args = ap.parse_args()
    main(k=args.k, run_sensitivity=not args.no_sensitivity)
