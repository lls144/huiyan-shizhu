# M8 Real PLC Acceptance Summary

- Generated: 2026-09-10T18:44:13.348+08:00
- PLC: `192.0.2.1`
- DB number: `3`
- Git commit: `f5d1fa0c7ee789766f953a6ab14f7d64ed96272c`
- Evidence boundary: AUTO reflects S7 DB/Q-state reads; it does not replace visual LED, physical button, or power-cycle evidence.

## Control-write confirmation

Every control write is read back and re-sent until the PLC really holds the requested value, because this CPU silently drops PUT/GET writes into `DB_M8_Acceptance.DBB0..7`.

- Confirmed control writes: 193
- Writes that needed a re-send: 86
- Most attempts used by one write: 10 (allowance: 12, interval: 0.02 s)

| Test | Status | Failure |
|---|---|---|
| M8-T01 | AUTO PASS |  |
| M8-T02 | AUTO PASS |  |
| M8-T03 | AUTO PASS |  |
| M8-T04 | AUTO PASS |  |
| M8-T05 | AUTO PASS |  |
| M8-T06 | AUTO PASS |  |
| M8-T07 | AUTO PASS |  |
| M8-T08 | AUTO PASS |  |
| M8-T09 | AUTO PASS |  |
| M8-T10 | AUTO PASS |  |
| M8-T11 | AUTO PASS |  |
| M8-T15 | AUTO PASS |  |
