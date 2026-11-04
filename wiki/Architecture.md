<!--
Purpose: System architecture for a marine alarm and automation wiring system.
Version: v1 (2026-11-04) — generic version.
Scope: PUBLIC — design principles applicable to any vessel.
Architecture: wiring-io wiki.
-->

# Architecture

## Principles

1. **The alarm panel is primary and standalone.** If the automation computer dies, the boat
   is back at passive-alarm behaviour **and the panel says so** (a heartbeat output that
   drops when the computer stops).

2. **Automation is advisory; its failure is announced.** The crew always has the final say.
   No automated action proceeds without the crew's ability to override it in copper.

3. **Manual control stays in copper.** Every automated load has a manual override that works
   with no software: a blower MANUAL switch, a water-heater bypass, a helm rocker for engine
   stop override. These are not software toggles — they are physical switches that break or
   make a circuit.

4. **Fail-safe direction is chosen per output:**
   - Engine kills: NC contacts in series. Dead computer = engine runs.
   - Charging permissives: NC contacts energise-to-disconnect. Dead relay = loads stay on.
   - Emergency loads (bilge pump): fed ahead of the breaker panel. Panel off = pump runs.

5. **I/O assignments are data.** One master table (io_master.yml in the automation-engine
   repo) maps every Modbus channel to a function. Code uses function names, never raw
   addresses. Move a channel in the table, not in the code.

6. **Build standard: boring and debuggable.** Everything is built so it can be diagnosed
   from the nav station with a multimeter and no internet connection.

## Layers

```
SENSORS ──────────────────────────────► ALARM PANEL (standalone, lamps, buzzer, mute)
        │ parallel tap (NPN, DI COM)          ▲ heartbeat output from automation computer
        ▼                                     ▲ anchor drag from anchor alarm
  DI modules (Modbus RTU)                     ▲ device relays, other hard-wired points
  Relay modules (Modbus RTU)
        │ RS-485 bus, one master
        ▼
  AUTOMATION COMPUTER (Pi or equivalent)
  ├── Rules engine (reads signals, drives relays)
  ├── History (InfluxDB or equivalent)
  ├── Dashboards / alerts
  └── Vessel ops (maintenance, inventory, cockpit display)
```

### The Modbus bus

All I/O modules sit on one RS-485 Modbus RTU bus (9600 8N1, one master at a time).
Module addressing follows a convention:

| Address | Role | Example |
|---|---|---|
| 1 | Existing relay module (legacy) | S6 |
| 2 | Control DI (status inputs) | S2 |
| 3 | New relay module | S3 |
| 4 | Safety DI (alarm inputs) | S1 |
| 5+ | Expansion (analog, additional DI/relay) | S5 |

The gateway (USB-RS485 adapter or Modbus TCP gateway) is the only bus master. The
automation computer talks to the gateway; the gateway talks to the modules.

## Commissioning workflow

Every circuit follows the same path:

1. **Ring out** — verify continuity of every wire with a meter, both ends labelled
2. **Wire from the sheet** — the rendered HTML page is the build document
3. **Prove it** — test the circuit aboard for its designed function (record an F-id)
4. **Owner's acceptance** — the owner says yes, the circuit is accepted
5. **Go live** — update io_master state to `live`; the matching automation rule activates
6. **Update the register** — record the proof and status in the circuit register

Nothing goes live without a test. Nothing gets wired that is not drawn.
