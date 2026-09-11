# M8 Real PLC Acceptance Summary

- Generated: 2026-09-11T11:01:13.816+08:00
- PLC: `192.0.2.1`
- DB number: `3`
- Git commit: `04b4622c669ac7dac0b902efb6afef802108d5d1`
- Evidence boundary: AUTO reflects S7 DB/Q-state reads; it does not replace visual LED, physical button, or power-cycle evidence.

## Control-write confirmation

Every control write is read back and re-sent until the PLC really holds the requested value, because this CPU silently drops PUT/GET writes into `DB_M8_Acceptance.DBB0..7`.

- Confirmed control writes: 193
- Writes that needed a re-send: 90
- Most attempts used by one write: 5 (allowance: 12, interval: 0.02 s)

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
