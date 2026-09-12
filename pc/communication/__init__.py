"""PC-to-PLC minimal command bridge for the non-vision side of the project.

This package intentionally does not import ``cv2`` or PySide6.  It consumes the
existing M4 ``VisionEvent`` objects and sends shape commands to a real S7-1200
using the TEST-ONLY ``M8_AcceptanceData`` DB layout defined in
``plc/src/PLC_Types.scl``.
"""

from .config import PlcCommunicationConfig, load_plc_communication_config
from .fake_plc import FakeAcceptancePlc
from .models import (
    PlcCommand,
    PlcCommandResult,
    PlcCommandStatus,
    PlcState,
    command_from_event,
    label_to_shape_code,
)
from .sink import (
    NullPlcSink,
    PlcCommandSink,
    RecordingPlcSink,
    S7PlcCommandSink,
    build_plc_sink,
)
from .acceptance import run_offline_acceptance, write_offline_acceptance

__all__ = [
    "FakeAcceptancePlc",
    "NullPlcSink",
    "PlcCommand",
    "PlcCommandResult",
    "PlcCommandSink",
    "PlcCommandStatus",
    "PlcCommunicationConfig",
    "PlcState",
    "RecordingPlcSink",
    "S7PlcCommandSink",
    "build_plc_sink",
    "command_from_event",
    "label_to_shape_code",
    "load_plc_communication_config",
    "run_offline_acceptance",
    "write_offline_acceptance",
]
