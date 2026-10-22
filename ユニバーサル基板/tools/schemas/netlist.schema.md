# CSV netlist schema

Exactly these four unique header fields: `net,ref,pin_number,pin_name`. UTF-8 (BOM accepted). All fields except physical pin_number are nonempty strings. Each (ref,pin_name) and each nonempty (ref,pin_number) must be unique. NC is a separate disconnected state for each pin. Parsed by the approved 基板/compare_netlist.py read_rows(key='name'). Physical footprint pin numbers are required and must agree with any supplied CSV number.
