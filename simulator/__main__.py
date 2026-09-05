"""Run M6 headless acceptance: python -m simulator --scenario all."""
import argparse
from pathlib import Path
from .models import Config
from .scenarios import NAMES
from .reporting import report, write_report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=("all", *NAMES), default="all")
    parser.add_argument("--config", type=Path, default=Path(__file__).parent / "config/fake_plc.json")
    parser.add_argument("--output-json", type=Path, default=Path("output/m6/m6-fake-plc-scenario-results.json"))
    parser.add_argument("--output-csv", type=Path, default=Path("output/m6/m6-fake-plc-scenario-results.csv"))
    args = parser.parse_args(argv)
    data = report(NAMES if args.scenario == "all" else [args.scenario], Config.load(args.config))
    write_report(data, args.output_json, args.output_csv)
    for item in data["scenarios"]:
        print(f"{item['scenario']:22} {'PASS' if item['passed'] else 'FAIL'}")
    print(f"deterministic replay: {data['deterministic_replay']}; benchmark: {data['benchmark']}")
    return 0 if data["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
