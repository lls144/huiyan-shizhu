"""Standalone CLI for manual PLC bridge checks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

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
    args = parser.parse_args()

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
