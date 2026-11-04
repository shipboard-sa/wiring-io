<!--
Purpose: How the wiring-plan system works — the register, sheet sources, IDs, build and change workflow.
Version: v1 (2026-11-04) — generic version.
Scope: STANDALONE UTILITY — documentation for the drawing system.
Architecture: Diagrams system (this folder). Read after the top-level README.
-->

# Wiring plans

## The drawing system

One YAML file per circuit, validated automatically, rendered to browsable/printable HTML.

### Sources

- `sheets/W<nn>.yml` — one per circuit. Each sheet has ladder rungs, a wire list, cable
  descriptions, build checks, and a commissioning test procedure.
- `register/devices.yml` — every device a wire lands on, with its terminals as marked on
  the physical part.
- `register/pool.yml` — Modbus relay channel assignments, cross-checked against the sheets.
- `register/questions.yml` — open design questions (Q#) that may move a wire or a decision.

### Build

```bash
python build.py            # validate + render out/index.html, out/register.html, out/W<nn>.html
```

Requires Python 3.8+ and PyYAML. The build:

1. Loads all register files and sheets
2. Validates every `DEVICE:TERMINAL` endpoint exists in `devices.yml`
3. Checks every ladder connection has a corresponding wire
4. Checks for duplicate wire IDs
5. Cross-checks relay channel usage against `pool.yml`
6. Renders HTML with ladder SVGs, wire lists, terminal landing tables

### Wire IDs

Wire IDs are the **printed label** on both ends of the physical wire: `W01-05` on the
sheet means `W01-05` on the heat-shrink sleeve at each end. A label traces straight back
to its sheet and its line in the YAML.

### Element types

| Type | YAML | Description |
|---|---|---|
| NC contact | `nc` | Normally closed; drawn with diagonal bar |
| NO contact | `"no"` | Normally open; **must be quoted** (bare `no` = YAML false) |
| NC switch | `switch_nc` | NC with manual actuator symbol |
| NO switch | `switch_no` | NO with manual actuator symbol |
| Coil / fuse | `coil` | Circle; for relay coils, fuses, any series device |
| Lamp | `lamp` | Circle with X; indicator lamp |
| Diode | `diode` | Triangle + bar; anode on the `a` terminal |

Any element may carry a `bypass:` (a parallel branch around it).

### YAML gotchas

- **Quote `"no"`** — bare `no` is YAML boolean false, not a contact type.
- **Quote values with `: `** — YAML treats `key: value` inside a string as a mapping.
- **Rebuild after every edit** — the validation catches typos before they reach the boat.

### Adding a new circuit

1. Create `sheets/W<nn>.yml` following the examples (W01, W02).
2. Add any new devices to `register/devices.yml` with their terminal names.
3. If the circuit uses a Modbus relay channel, assign it in `register/pool.yml`.
4. Run `python build.py` — fix any validation errors.
5. Open `out/W<nn>.html` in a browser to review the ladder and wire list.
6. Print landscape for field use.
