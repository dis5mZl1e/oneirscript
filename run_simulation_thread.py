"""Opt-in P6 snapshot client with an isolated default save directory."""
from __future__ import annotations

import argparse
from pathlib import Path


def main(argv=None):
    parser = argparse.ArgumentParser(description='Oneirscript P6 snapshot client')
    parser.add_argument('--save-dir', type=Path, default=Path('outputs/p6-threaded-save'))
    parser.add_argument('--seed', type=int, default=20261105)
    parser.add_argument('--smoke', action='store_true')
    parser.add_argument('--no-save', action='store_true')
    parser.add_argument('--process', action='store_true',
                        help='run the snapshot client with an independent simulation process')
    args = parser.parse_args(argv)

    from dream_demo.core import GameState
    from dream_demo.persistence import SaveManager
    from dream_demo.simulation_worker import SimulationWorker
    from dream_demo.ui.simulation_snapshot import SnapshotApp, render_snapshot

    manager = SaveManager(args.save_dir)
    state = manager.load() if manager.primary.exists() else GameState.new(seed=args.seed)
    if args.process:
        from dream_demo.simulation_process import SimulationProcess
        worker = SimulationProcess(state, save_dir=args.save_dir,
                                   persistence_enabled=not args.no_save)
    else:
        worker = SimulationWorker(state, manager_factory=lambda: SaveManager(args.save_dir),
                                  persistence_enabled=not args.no_save)
    try:
        if args.smoke:
            from rich.console import Console
            worker.ready.result(timeout=30)
            completion = worker.submit('wait').result(timeout=30)
            Console(legacy_windows=False).print(render_snapshot(completion.snapshot, 80, 24))
            print('snapshot_sequence:', completion.snapshot.sequence)
        else:
            app = SnapshotApp(worker)
            app.run()
            if app._exception is not None:
                raise app._exception
    finally:
        worker.close(save=not args.no_save, timeout=30)


if __name__ == '__main__':
    main()
