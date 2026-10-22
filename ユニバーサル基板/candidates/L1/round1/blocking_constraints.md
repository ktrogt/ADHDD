# L1 blocking constraints — no relaxation applied

2026-10-22. These are conflicts between approved geometric inputs, not proposed circuit changes. Canonical `verify` remains FAIL. Re-run `prove_constraints.py` using the prescribed Python; it reads shared inputs and writes only L1/constraint_reproduction.json.

| Hard requirement | Reproduction / candidate | Smallest relevant adjustment for this build (pending Claude) |
|---|---|---|
| P05/P06 ceramic <=2 holes; M01 bodies >=0.4 hole; P11/P12 coil <=4 holes | At carrier rotation 270°, only one ceramic placement satisfies P05+M01, and only three connector placements satisfy P11+M01. None coexist at M01 clearance, even before adding the bulk can. | Ceramic placement and route bounds **3 holes**; keep coil <=4 and body clearance unchanged. |
| P13/P14 DC-DC caps <=4 holes; H07 can-to-converter >=1 hole | For either cap, no origin/rotation satisfies the adopted 18.42×16.10 mm converter envelope and H07 at P13=4 or 5. | Both cap placement/route bounds **6 holes**, or supervisor-corrected verified converter envelope. |
| P15 buffer bypass <=2 holes; M01 >=0.4 hole | No bypass placement works at 2 or 3; the DIP6 carrier envelope is 11×8 mm. | P15 **4 holes**, P16 **4 holes** (currently 3), or approved carrier/decoupling geometry correction. |
| V02/V03 R210/filter junction <=2 holes; M01 >=0.4 hole | A 3-hole resistor and 2-hole capacitor have no nonoverlapping two-end placement at bound 2. | Bound **3 holes for the offending R210 endpoint only**; other source/return links stay <=2. |
| P02 TVS-to-bulk shortest route <=3 holes; M01 >=0.4 hole | No solution even with diagonal insulated wires: the best possible Euclidean worst endpoint is sqrt(17)=4.123 holes. Minimum feasible Manhattan bound is 5. | Both routes **5 holes** for the all-bare candidate, or approved TVS/bulk lead-envelope correction. |
| Conservative board-edge model | Four identical thermal channel tiles need 14-hole pitch. Integer origins require first carrier x>=6 and final x<=47 under the model, but 6+3×14=48. Candidate starts x=5; C311 spills 1.49 mm beyond the fictitious edge. All pins remain valid; nominal real-board body clearance is positive. | Teach tooling the actual 155×114 mm outline / derived grid origin, then re-audit mounting, access and mechanical tolerance. Do not silently enlarge copied board.json. |
| M02 mounting centres >=5.08 mm from real board edge | Approved board drawing gives **5.00 mm**, independent of placement. | Accept the board's **5.00 mm nominal** or select a different board through the supervisor. |
| W07 coil harness copper >=0.28 mm² | Approved parts-fit record specifies AWG26 precrimp131312, approximately 0.129 mm². Harness is outside this layout model. | Supervisor reconciles the approved cable choice with W07; no different cable purchased/assumed. |

The first five geometric reproductions exhaust all four rotations and all integer origins in [-12,12]². Near limits bound every relevant first-pin origin inside this domain. The ceramic/coil coupling is tested at the F1 270° carrier orientation. The converter/buffer/divider/TVS conflicts are independent of translating or rotating the complete block, so moving them elsewhere on the board cannot solve them.

Tool limitations retained honestly:

- Full audit: 27 hard PASS, 9 hard FAIL, 25 hard UNCHECKED. Unsupported feature access, pad/lead/solder surface clearances, branch current/drop, off-board harnesses, supports and bench evidence cannot be made PASS by placement alone.
- C01 always reports scope provenance UNCHECKED; L1's netlist.csv is byte-identical to approved netlist_ub.csv, and its SHA256 is in metrics_extra.json.
- The CLI's default numerical score is not the T7 weighted/lexicographic score. T7 atomic penalties are exported separately, with unresolved soft checks explicitly excluded from its lower bound.
- The shared router rejects any BODY_OFFBOARD and does not preserve hierarchical GND/VREF stars. `route_l1.py` reuses its A* locally with separate branch occupancy; canonical verify remains authoritative and unmodified. `finish.py` removes duplicate/collinear wire pieces, invokes the prescribed CLI and moves SVG text only.

No source hashes, footprint envelopes, net assignments or hard rules were altered to hide these conditions. Claude must decide between corrected verified footprints, explicit numeric rule revisions, or a different board. Re-run all audits after any approved change.
