<!--
Purpose: Entry point for the wiring-io repo — YAML-driven wiring documentation for marine alarm/automation systems.
Version: v1 (2026-11-04)
Scope: PUBLIC — generic reference for any vessel's electrical build.
Architecture: Diagrams/build.py validates and renders YAML wiring sheets to HTML.
-->

# Wiring I/O — Marine Alarm and Automation Wiring System

A YAML-driven wiring documentation system for marine alarm and automation installations.
Write your wiring plans as structured YAML, validate them automatically, and render them
to browsable HTML — ladder schematics, wire lists, terminal landings, and commissioning
checklists.

This repo is part of the [Ship's Automation](https://github.com/shipboard-sa/guide)
open-source project.

## What this does

- **YAML wiring sheets** — one file per circuit, with ladder rungs, wire lists, cable runs,
  as-built comparison notes, build checks, and commissioning tests
- **Device register** — every device a wire lands on, with terminal names as marked on the part
- **Relay pool** — Modbus relay channel assignments, tracked and cross-checked
- **Automated validation** — `build.py` catches unknown devices, missing wires, duplicate IDs,
  and pool/sheet mismatches before you print and wire
- **HTML output** — browsable, printable pages with ladder schematics (SVG), wire lists, and
  terminal landing tables; dark mode supported

## Quick start

```bash
cd Diagrams
python build.py          # validate + render -> out/index.html
```

Requires Python 3.8+ and PyYAML (`pip install pyyaml`).

Open `out/index.html` in a browser. Print landscape for field use.

## Repo structure

```
Diagrams/
  build.py               # validator + renderer
  README.md              # how the drawing system works
  register/
    devices.yml          # every device, its terminals, location
    pool.yml             # Modbus relay channel assignments
    questions.yml        # open questions (Q#) that may move a design
  sheets/
    W01.yml              # example: bilge pump feed circuit
    W02.yml              # example: engine kill circuit
  out/                   # generated HTML (gitignored)
wiki/
  Architecture.md        # system design principles
  Wiring-Sheets.md       # how the drawing system works, sheet index
  Commissioning.md       # ring-out, prove, accept, live workflow
```

## The YAML wiring sheet format

Each sheet describes one circuit:

```yaml
id: W01
title: Bilge pump feed ahead of the breaker panel
version: v1
group: A (install first)
purpose: >
  Feed the automatic bilge pump from the battery bus ahead of the main
  breaker panel, so it runs even with the panel off.
slides: []
refs: []

rungs:
  - title: Pump feed from battery bus
    start: {at: "BAT:POS", label: "Battery bus +24 V"}
    elements:
      - {type: coil, dev: F1, a: IN, b: OUT, label: "F1 15 A ATC fuse"}
    end: {at: "BP:FEED", label: "Bilge pump power input"}

wires:
  - {id: W01-01, a: "BAT:POS", b: "F1:IN", awg: "14", run: "battery bay to nav station"}
  - {id: W01-02, a: "F1:OUT", b: "BP:FEED", awg: "14", run: "nav station to bilge"}

cables:
  C1: "Battery bay to nav station, 14 AWG pair, fire sleeve in the engine room."

checks:
  - "Fuse holder: confirm 15 A ATC rated for 24 V DC."
  - "Heat-shrink labels at both ends: W01-01, W01-02."

test:
  - "Meter: 24 V at BP:FEED with the fuse in; 0 V with it pulled."
  - "Float switch test: raise the float; pump runs; lower it; pump stops."
```

### Element types

| Type | Symbol | Meaning |
|---|---|---|
| `nc` | Normally closed contact | Opens to break the circuit |
| `"no"` | Normally open contact | Closes to make the circuit (quote it — YAML reads bare `no` as false) |
| `switch_nc` | NC switch | Manual NC switch with actuator symbol |
| `switch_no` | NO switch | Manual NO switch with actuator symbol |
| `coil` | Coil / fuse | Relay coil, fuse, or any series device |
| `lamp` | Lamp | Indicator lamp |
| `diode` | Diode | Anode on the `a` terminal |

### Endpoints

Every wire endpoint is `DEVICE:TERMINAL` — the build rejects any endpoint not in
`register/devices.yml`. This catches typos and ensures every wire lands on a real terminal.

### Wire IDs

Wire IDs are the **printed label** on both ends of the wire: `W01-05` on the sheet means
`W01-05` on the heat-shrink sleeve. A label traces straight back to its sheet and its line
in the YAML.

## Adapting this for your boat

1. **Define your devices** — edit `register/devices.yml` with your modules, relays, fuse
   holders, switches, and sensors. List every terminal as marked on the part.
2. **Define your relay pool** — edit `register/pool.yml` with your Modbus relay modules and
   channel assignments.
3. **Write your sheets** — one `sheets/W<nn>.yml` per circuit. Follow the examples.
4. **Build and check** — `python build.py` validates everything and renders HTML.
5. **Wire from the output** — print the HTML pages landscape; they have the ladder, wire
   list, terminal landings, and test procedure.

The [New Owner's Guide](https://github.com/shipboard-sa/guide) walks through the full
process with your AI assistant.

## Related repos

| Repo | Role |
|---|---|
| [automation-engine](https://github.com/shipboard-sa/automation-engine) | Rules engine that drives the relays these sheets wire |
| [alarm-panel](https://github.com/shipboard-sa/alarm-panel) | Custom alarm panel PCB — a consumer of these circuits |
| [vessel-ops](https://github.com/shipboard-sa/vessel-ops) | Tracks parts, spares, and maintenance for every device |

## License

MIT — see [LICENSE](LICENSE).
