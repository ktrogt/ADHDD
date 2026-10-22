"""Check T1 CSV inventory and pin coverage; does not approve unresolved engineering holds."""
import csv
import sys
from collections import Counter
from pathlib import Path


def main():
    root=Path(__file__).resolve().parent
    with (root/'parts.csv').open(encoding='utf-8-sig',newline='') as stream:
        parts=list(csv.DictReader(stream))
    with (root/'netlist_expected.csv').open(encoding='utf-8-sig',newline='') as stream:
        rows=list(csv.DictReader(stream))
    expected={}
    refs=set()
    footprints={}
    for part in parts:
        ref=part['ref']
        assert ref not in refs, f'duplicate ref {ref}'
        refs.add(ref)
        assert part['populate'] in ('yes','DNP'),ref
        assert part['confidence'] in ('primary','secondary','assumption'),ref
        assert all(part.values()), f'empty parts field {ref}'
        local_names=set()
        for spec in part['pins'].split(';'):
            number,name=spec.split(':',1)
            assert number and name and name not in local_names,ref
            local_names.add(name)
            identity=ref,number
            assert identity not in expected,identity
            expected[identity]=name
        footprint=part['footprint']
        details=part['footprint_details'],part['dimension_source']
        assert footprint not in footprints or footprints[footprint]==details,footprint
        footprints[footprint]=details
    actual=Counter()
    for row in rows:
        assert row['ref'] in refs, f'unknown ref {row}'
        identity=row['ref'],row['pin_number']
        assert identity in expected, f'unknown pin {row}'
        assert expected[identity]==row['pin_name'], f'pin name mismatch {row}'
        assert row['net'], f'empty net {row}'
        actual[identity]+=1
    assert set(actual)==set(expected), 'missing pins'
    assert all(count==1 for count in actual.values()), 'repeated pin rows'
    net_counts=Counter(row['net'] for row in rows if row['net']!='NC')
    assert all(n>=2 for n in net_counts.values()), f'singleton net: {net_counts}'
    allowed=set('VIN_RAW VIN_FUSED VIN_PROT VM +5V VSYS +3V3 GND SN_BUS SN_RX_IN SN_PU UART_RX VREF ARM ARM_SW SLEEP FAULT MUX_S0 MUX_S1 I_SENSE T_SENSE VM_SENSE'.split())
    for n in range(1,5):
        allowed.update(f'HDD{n}_{suffix}' for suffix in ('IN1','IN2','OUT1','OUT2','CS','CS_F'))
        allowed.add(f'NTC{n}')
    assert set(net_counts)==allowed, f'unexpected/missing net names {set(net_counts)^allowed}'
    jack=next(p for p in parts if p['ref']=='J101')
    assert jack['footprint']=='MJ179PH_PLACEHOLDER', 'J101 must retain explicit placeholder package'
    assert jack['pins']=='1:CENTER;2:SLEEVE;3:SWITCH', 'J101 logical pins changed'
    assert jack['confidence']=='assumption', 'J101 physical placeholder must remain unverified'
    assert 'PCB-stage HOLD: replace pad/slot geometry before layout' in jack['notes']
    pop=Counter(p['populate'] for p in parts)
    confidence=Counter(p['confidence'] for p in parts)
    print(f'PASS: {len(parts)} refs ({pop["yes"]} yes, {pop["DNP"]} DNP), {len(footprints)} footprint IDs')
    print(f'PASS: {len(expected)} declared pins, {len(rows)} rows; every ref/pin/name exists exactly once')
    print(f'PASS: {len(net_counts)} named nets; all have >=2 pins; {sum(r["net"]=="NC" for r in rows)} separate NC pins')
    print(f'CONFIDENCE: primary={confidence["primary"]}, secondary={confidence["secondary"]}, assumption={confidence["assumption"]}')
    print('PCB-STAGE HOLD: J101 placeholder pad/slot geometry must be replaced before layout; schematic baseline approved by Claude')
    return 0


if __name__=='__main__':
    try:
        sys.exit(main())
    except (AssertionError,KeyError,ValueError,OSError,csv.Error) as error:
        print(f'FAIL: {error}',file=sys.stderr)
        sys.exit(1)
