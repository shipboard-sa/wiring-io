<!--
Purpose: How the wiring sheet system works — format, conventions, build process.
Version: v1 (2026-11-04) — generic version.
Scope: PUBLIC — documentation for the YAML wiring sheet format.
Architecture: wiring-io wiki.
-->

# Wiring sheets

## The drawing system

- **Sources:** `Diagrams/sheets/W<nn>.yml` (one per circuit) + `Diagrams/register/`
  (devices, pool, questions).
- **Build:** `python build.py` validates and renders `out/index.html`, `out/register.html`,
  `out/W<nn>.html` (ladder schematic, wire list, per-device terminal landings, build checks,
  commissioning test). Print landscape from a browser for field use.
- **Wire ID = printed label** on both ends (`W01-05`). A label traces straight back to its
  sheet and its line in the YAML.
- **YAML gotchas:** quote `"no"` (bare `no` = YAML false); quote values containing `: ` or
  ` #`; rebuild after every edit.

## Sheet anatomy

Each sheet YAML file contains:

| Section | Purpose |
|---|---|
| `id`, `title`, `version` | Identity and change tracking |
| `group` | Build priority (A = install first, B = pre-wire, C = software only) |
| `purpose` | What the circuit does and why |
| `rungs` | Ladder schematic — the circuit logic |
| `wires` | Every physical wire, with endpoints, gauge, and routing |
| `cables` | Multi-conductor cable descriptions |
| `checks` | Things to verify during the build |
| `test` | Step-by-step commissioning test procedure |
| `changelog` | Version history |

## Rungs (the ladder schematic)

Each rung is a series circuit from `start` to `end`, with elements (contacts, coils, etc.)
in between. The build renders these as SVG ladder diagrams.

```yaml
rungs:
  - title: "Description of this rung"
    start: {at: "DEVICE:TERMINAL", label: "Human-readable label"}
    elements:
      - {type: nc, dev: RELAY, a: COM, b: NC, label: "What this contact does"}
    end: {at: "DEVICE:TERMINAL", label: "Human-readable label"}
    note: "Engineering notes — failure modes, design reasoning"
```

An element may carry a `bypass:` — a parallel path around it (drawn as a vertical branch
in the ladder):

```yaml
elements:
  - {type: nc, dev: S3, a: R1-COM, b: R1-NC, label: "Software stop",
     bypass: {type: "no", dev: R34, a: "14", b: "11", label: "Bypass relay"}}
```

## Conventions

- **One sheet per circuit** — a circuit is a self-contained function (bilge pump feed,
  engine kill, blower control). If two functions share no wires, they are separate sheets.
- **Wire IDs are sequential within a sheet** — `W01-01`, `W01-02`, etc. Retired wire IDs
  are not reused (comment them out with a note).
- **Device IDs are short and stable** — `R29` for relay 29, `S1` for Modbus module at
  address 1, `BP1` for bilge pump 1. Once assigned, a device ID does not change.
- **Groups** control build order:
  - **A** — install and test with no software. These circuits work with the automation
    computer off.
  - **B** — pre-wire now (harmless unpowered), but needs software to function.
  - **C** — software-only changes (rule configuration, no physical wiring).
