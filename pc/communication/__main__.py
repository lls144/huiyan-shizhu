"""Standalone CLI for manual PLC bridge checks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .acceptance import run_offline_acceptance, write_offline_acceptance
from .config import load_plc_communication_config
from .sink import RecordingPlcSink, S7PlcCommandSink, build_plc_sink


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("pc/config/plc.json"))
    parser.add_argument("--dry-run", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)

    send_parser = subparsers.add_parser("send", help="send one shape command")
    send_parser.add_argument("--shape", choices=("triangle", "rectangle", "circle"), required=True)
    send_parser.add_argument("--semantic-id", type=int, required=True)

    subparsers.add_parser("dequeue", help="send one dequeue request")
    subparsers.add_parser("reset", help="send one reset request")
    acceptance_parser = subparsers.add_parser(
        "acceptance",
        help="run the offline non-vision bridge acceptance scenarios",
    )
    acceptance_parser.add_argument("--output-dir", type=Path, default=Path("output/m8-bridge"))
    args = parser.parse_args()

    if args.command == "acceptance":
        document = run_offline_acceptance()
        json_path, csv_path = write_offline_acceptance(document, args.output_dir)
        print(json.dumps(document["summary"], indent=2))
        print(str(json_path))
        print(str(csv_path))
        return 0 if document["summary"]["all_scenarios_pass"] else 1

    config = load_plc_communication_config(args.config)
    if args.dry_run:
        sink = RecordingPlcSink()
    else:
        built = build_plc_sink(config)
        if built is None:
            raise SystemExit("PLC communication is disabled; pass --dry-run for an in-memory run")
        sink = built

    try:
        sink.start()
        if args.command == "send":
            from pc.events.models import EventType, VisionEvent

            event = VisionEvent(
                event_id=1,
                event_type=EventType.OBJECT_ENTER,
                object_id=args.semantic_id,
                label=args.shape,
                confidence=1.0,
                frame_index=0,
            )
            result = sink.send_event(event)
        elif args.command == "dequeue":
            result = sink.dequeue()
        else:
            result = sink.reset()
        print(json.dumps(result.to_record(), indent=2, ensure_ascii=False))
        return 0
    finally:
        sink.stop()


if __name__ == "__main__":
    raise SystemExit(main())
