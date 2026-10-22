# Deliberate faults

`wiring.json`: A and B bare wires cross at D3 (short); C has no wire (open).
`wiring.valid.json`: insulated B crossing, all nets connected, NC H8 isolated.
Run ub.py verify --project tools/fixtures/faults: expected exit 1, SHORT + BARE_CROSSING + LVS:SPLIT.
