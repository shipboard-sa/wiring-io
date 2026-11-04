<!--
Purpose: Commissioning workflow — how to test and accept each circuit.
Version: v1 (2026-11-04) — generic version.
Scope: PUBLIC — applicable to any vessel's alarm/automation build.
Architecture: wiring-io wiki.
-->

# Commissioning

## The workflow

Every circuit follows the same path from drawing to live operation:

### 1. Ring out

Before powering anything, verify every wire with a meter:

- **Continuity** — each wire from end to end, both conductors of a pair
- **No shorts** — between conductors in the same cable, and to ground
- **Labels match** — the heat-shrink sleeve at each end matches the wire ID in the sheet
- **Terminal landings** — each wire is on the correct screw/terminal as shown in the
  terminal landings table

Record the ring-out as a finding (F-id) with date and result.

### 2. Wire from the sheet

The rendered HTML page (`out/W<nn>.html`) is the build document. It has:

- The ladder schematic showing the circuit logic
- The wire list with every wire, its gauge, and its routing
- The terminal landings table showing what goes on each screw
- Build checks — things to verify during the build
- The commissioning test — step-by-step verification

Print it landscape. Take it to the boat.

### 3. Prove it

Run the commissioning test procedure from the sheet. Each test step verifies one aspect
of the circuit's designed function:

- **Bench tests** — verify relay contact operation before installation
- **Powered tests** — verify the circuit works as designed with the actual loads
- **DI verification** — confirm the automation system reads the correct state
- **Edge cases** — verify fail-safe behaviour (what happens when power is lost, a wire
  breaks, a relay fails)

Record each test result as a finding (F-id).

### 4. Owner's acceptance

The owner reviews the test results and says yes. This is a gate — nothing goes live
without it.

### 5. Go live

Update the io_master table: set the circuit's `state: live`. The matching automation
rule(s) now activate. Monitor the first hours of operation.

### 6. Update the register

Record in the circuit register:
- Which sheet, which version
- Ring-out finding (F-id)
- Proof finding (F-id)
- Date accepted
- What is left (if anything — a future software rule, a label, a tidy-up)

## The D/F register method

Track every decision and finding with a sequential ID:

- **D-nnn** — a decision (a choice that was made, with reasoning)
- **F-nnn** — a finding (a fact that was established, with evidence)

Decisions reference the findings that informed them. Findings reference the tests or
observations that established them. This creates a traceable chain from requirement to
implementation to proof.

## Safety rules

- **No coil writes without the owner at the helm** — relay modules that control
  engine-critical functions (kill contacts, permissives) are only written when the owner
  can verify the physical result.
- **Announce automation outages** — if the automation computer goes down for maintenance,
  tell the crew. Bilge pumps on automatic may stop if they depend on a relay that defaults
  to the wrong state.
- **Test the fail-safe direction** — for every relay, verify what happens when the relay
  loses power. The answer must match the designed fail-safe direction in the architecture.
