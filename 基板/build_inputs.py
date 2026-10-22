"""Reproduce the two T1 CSV files. Refuses to overwrite existing output files."""
import csv
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
A = 'https://akizukidenshi.com/catalog/g/g'
G = 'https://akizukidenshi.com/goodsaffix/'
S = {
    'pico': 'https://datasheets.raspberrypi.com/pico/Pico-2-Pinout.pdf',
    'picodim': 'https://datasheets.raspberrypi.com/pico/pico-product-brief.pdf',
    'pololu': 'https://www.pololu.com/product/4035',
    'polpin': 'https://a.pololu-files.com/picture/0J11426.1200.jpg',
    'poldim': 'https://www.pololu.com/file/0J1882/drv887x-single-brushed-dc-motor-driver-carrier-dimensions.pdf',
    'buffer': 'https://www.diodes.com/assets/Datasheets/74AHC1G125.pdf',
    'mux': 'https://toshiba.semicon-storage.com/info/TC74HC4052AP_datasheet_en_20161018.pdf?did=16132&prodName=TC74HC4052AP',
    'muxdim': 'https://toshiba-semicon-storage.com/cn/semiconductor/product/general-purpose-logic-ics/detail.TC74HC4052AP.html',
    'mj': G+'mj179ph_mj180ph.pdf',
    'mjpage': 'https://www.est-marushin.co.jp/prod/mj/J179PH.html',
    'mjdraw': 'https://www.est-marushin.co.jp/img/drw/MJ179PH.jpg',
    'm78': G+'m78ar-1.pdf',
    'r': G+'mf_FAITHFUL%20LINK.pdf',
    'c100': G+'Multilayer_capacitor.pdf',
    'c220': G+'RDER71H224K1K1H03B.pdf',
    'cp': G+'zlh.pdf',
    'vh': G+'VH.pdf', 'xh': G+'xh.pdf', 'ph': G+'PH.pdf',
    'hdr': G+'PH-1xXXSG-AD.pdf', 'socket': G+'FHU-1.pdf',
    'fuse': G+'mfr.pdf', 'd5822': G+'1N5822.pdf',
    'd5819': G+'1n5819.pdf', 'bat': G+'bat43.pdf', 'tvs': G+'P4KE.pdf',
}

# Dimensions: mm. Drills are finished plated hole sizes, not pre-plating tool sizes.
# Every RECOMMENDED pad/drill/pitch below is an engineering choice, not a maker claim.
FP = {
    'R_AXIAL_P7.62': ('Horizontal axial; MFS25 body L=3.3 nominal (max4.0), D=1.8+/-0.3; lead d=0.45+/-0.05. RECOMMENDED pitch7.62, drill0.80, padD1.80; pin1=(0,0),pin2=(7.62,0); nonpolar.', S['r']),
    'C_RADIAL_P2.54': ('Radial straight; pitch2.54; R15 body W<=3.8,T<=2.8,H<=3.8; lead d=0.50+/-0.05. RECOMMENDED drill0.80,padD1.70; pin1=(0,0),pin2=(2.54,0); nonpolar.', S['c100']),
    'C_RADIAL_P5.0': ('Radial; pitch5.0+/-0.8; body L<=4.5,T<=3.15,H<=3.5; lead d=0.50+/-0.05. RECOMMENDED drill0.80,padD1.80; pin1=(0,0),pin2=(5,0); nonpolar.', S['c220']),
    'CP_RADIAL_D10_P5.0': ('Pitch5.0+/-0.5; can D10,L16 nominal; sleeve envelope D<=10.5,H<=17.5; lead d0.60. RECOMMENDED drill0.90,padD2.0; pin1=POS(0,0),pin2=NEG(5,0); square pin1,+silk; sleeve stripe=NEG.', S['cp']+' | '+A+'102719/'),
    'CP_RADIAL_D6.3_P2.5': ('Pitch2.5+/-0.5; can D6.3,L11 nominal; envelope D<=6.8,H<=12.5; lead d0.50. RECOMMENDED drill0.80,padD1.70; pin1=POS(0,0),pin2=NEG(2.5,0); square pin1,+silk; sleeve stripe=NEG.', S['cp']+' | '+A+'102724/'),
    'D_DO201AD_P15.24': ('Axial horizontal DO201AD; body L7.2..9.5,D4.8..5.3; lead d1.2..1.3. RECOMMENDED pitch15.24,drill1.60,padD3.0; pin1=K(0,0),pin2=A(15.24,0); band/Ksilk at pin1; heat clearance.', S['d5822']),
    'D_DO41_P10.16': ('Axial horizontal DO41; body L<=5.2,D<=2.7; lead d<=0.90 (1N5819),<=0.86(P4KE). RECOMMENDED pitch10.16,drill1.20,padD2.40; pin1=K(0,0),pin2=A(10.16,0); band/Ksilk at pin1.', S['d5819']+' | '+S['tvs']),
    'D_DO35_P7.62': ('Axial horizontal DO35; store body3.8 x2.0. RECOMMENDED pitch7.62,drill0.80,padD1.80; pin1=K(0,0),pin2=A(7.62,0); band/Ksilk at pin1. Lead d<=0.55 is ASSUMED for sizing; verify actual lead fit.', A+'113907/ | '+S['bat']),
    'F_MFR300_P5.1': ('Radial Style2; pitch5.1+/-0.7; W<=12.0,H<=18.3,T<=3.0; lead d0.81. RECOMMENDED drill1.10,padD2.40; pin1=(0,0),pin2=(5.1,0); nonpolar; avoid diode heat.', S['fuse']),
    'M78AR05_1_SIP3': ('SIP3 pitch2.54; body11.5 x7.55 x10.2; rectangular leads0.70 x0.50(+/-0.05). RECOMMENDED drill1.20,padD2.10. Pins1VIN,2GND,3VOUT per maker p3 BOTTOM VIEW. Exact body offset and top-view orientation must be copied from that drawing; not visually transcribed here.', S['m78']),
    'MJ179PH_PLACEHOLDER': ('SCHEMATIC PLACEHOLDER: 3 pads named1/2/3 for CENTER/SLEEVE/SWITCH; no claimed physical pad positions,drills or slot sizes. Outline verified visually by Claude: body W9 xH11 xD14.5; jack axis6.5 above board; terminals protrude3.5 below board. Manufacturer outline does not specify PCB hole/slot pattern. PCB-stage HOLD: replace pad/slot geometry before layout; measure real part or obtain detailed drawing.', S['mj']+' | '+A+'106568/ | '+S['mjpage']+' | '+S['mjdraw']),
    'HDR_1X2_P2.54': ('Cut 1x2 from PH-1x40SG; pitch2.54; store recommended finished hole1.02; body thickness2.5,height2.5,tail3.0,contact6.1; cut length5.08 is calculated. RECOMMENDED main-board drill1.10,padD2.10; square pin1=(0,0),pin2=(2.54,0); silk both net names.', S['hdr']+' | '+A+'100167/'),
    'RPI_PICO_SOCKET': ('TOP USB at top: pin1 upper left=(0,0); pins1..20 down left at pitch2.54; pins40..21 down right x17.78,y0..48.26. Body21 x51; calculated centered bounds x=-1.61..19.39,y=-1.37..49.63. Two FHU-1x20SG sockets H8.5,thickness2.5,tail3.0; store recommended finished socket hole1.02. RECOMMENDED main-board drill1.10,padD2.0. Square pin1; no SWD pads; USB/BOOTSEL clearance.', S['picodim']+' | '+S['socket']+' | '+A+'105779/'),
    'POLOLU_4035_SOCKET': ('TOP components visible,VIN upper right: left pins1..7=(VM,GND,IN1,IN2,PMODE,SLEEP,VREF),x0,y0..15.24,pitch2.54; right pins14..8 top-to-bottom=(VIN,GND,OUT1,OUT2,IMODE,FAULT,CS),x12.70. Body15.2 x17.8; edge offset1.27 nominal; edge tolerance+/-0.3,hole location+/-0.1. Carrier holesD1.02 are distinct from socket-tail holes. Two FHU-1x7SG H8.5,thickness2.5,tail3.0; store recommended socket hole1.02. RECOMMENDED main-board drill1.10,padD2.0. Local counterclockwise numbering,not DRV8874 IC numbers; square pin1VM.', S['poldim']+' | '+S['socket']+' | '+A+'105779/'),
    'SOT23_5_SOT25': ('W5=SOT25,not SOT353; lead pitch0.95; body nominal3.0 x1.6,max3.1 x1.7; lead span2.7..3.0,H<=1.30. TOP pin1 lower-left,2 lower-middle,3 lower-right,4 upper-right,5 upper-left. RECOMMENDED pad centers1(-0.95,-1.10),2(0,-1.10),3(0.95,-1.10),4(0.95,1.10),5(-0.95,1.10); pad0.60 x1.20; no drill; pin1dot.', S['buffer']),
    'DIP16_W7.62_P2.54': ('DIP16-P-300-2.54A; pitch2.54,row7.62; body19.25 x6.4 nominal,Lmax19.75. TOP notch up: pin1upper-left to8lower-left,9lower-right to16upper-right. RECOMMENDED drill1.0,pad1.7 x2.0,square pin1. Lead fit must be checked against package drawing before release.', S['mux']+' | '+S['muxdim']),
    'JST_VH_B2P_P3.96': ('B2P-VH vertical2P; pitch3.96; maker finished hole1.65(+0.1/-0); body width7.86. RECOMMENDED padD3.20; square1(0,0),2(3.96,0). Copy keyed body outline/circuit1 orientation from VH.pdf p3 TOP type; p1 PCB layout is SOLDER SIDE,not top view.', S['vh']),
    'JST_XH_B2B_2P_P2.50': ('B2B-XH-A vertical2P; pitch2.50,not2.54; maker finished hole0.90(+0.1/-0); body width7.4. RECOMMENDED padD1.90; square1(0,0),2(2.5,0). Copy keyed outline/circuit1 orientation from xh.pdf TOP type; observe solder-side/top-view distinction.', S['xh']),
    'JST_PH_B2B_2P_P2.0': ('B2B-PH-K-S vertical2P; pitch2.0; maker finished hole0.70(+0.1/-0); body5.9 x4.5,height6.0. RECOMMENDED padD1.50; square1(0,0),2(2,0). Copy keyed outline/circuit1 mark from PH.pdf p2 TOP type.', S['ph']),
    'TP_THT_D2.5': ('Bare plated test pad,no bought component. DESIGN CHOICE finished drill1.0,padD2.5; pin1TP=(0,0); silk net name; no polarity.', 'Task T1 test-point requirement; design choice'),
}

COLS = 'ref,sheet,block,value,description,part_number,store_code,populate,footprint,footprint_details,pins,pinout_source,dimension_source,confidence,notes'.split(',')
parts, nets = [], []
PASSIVE = [(1,'P1'),(2,'P2')]
DIODE = [(1,'K'),(2,'A')]


def add(ref,sheet,block,value,description,pn,code,pop,foot,pins,connections,source,confidence='primary',notes=''):
    assert len(pins)==len(connections)
    assert ref not in {p['ref'] for p in parts}
    assert len({str(n) for n,_ in pins})==len(pins)
    assert len({name for _,name in pins})==len(pins)
    details,dimensions=FP[foot]
    parts.append(dict(zip(COLS,[ref,str(sheet),block,value,description,pn,code,pop,foot,details,
                               ';'.join(f'{n}:{name}' for n,name in pins),source,dimensions,confidence,notes])))
    nets.extend(dict(net=net,ref=ref,pin_number=str(n),pin_name=name) for (n,name),net in zip(pins,connections))


def cap(ref,sheet,block,value,a,b,pop='yes'):
    pn,code,foot={
        '470uF/35V':('35ZLH470MEFC10X16','102719','CP_RADIAL_D10_P5.0'),
        '100uF/35V':('35ZLH100MEFC6.3X11','102724','CP_RADIAL_D6.3_P2.5'),
        '100nF/50V':('R15X7R104J2L705Y','131527','C_RADIAL_P2.54'),
        '220nF/50V':('RDER71H224K1K1H03B','108146','C_RADIAL_P5.0'),
    }[value]
    polar=foot.startswith('CP_')
    add(ref,sheet,block,value,'Rubycon ZLH electrolytic' if polar else 'Radial X7R ceramic',pn,'Akizuki '+code,pop,foot,
        [(1,'POS'),(2,'NEG')] if polar else PASSIVE,[a,b],S['cp'] if polar else A+code+'/',
        notes='Local passive numbering. Negative sleeve stripe at2.' if polar else 'Nonpolar. Maker dimensions from sheet linked by store.')


def resistor(ref,sheet,block,value,a,b,pop='yes',note=''):
    pn,code={
        '1k':('MFS25F1KB','108535'),'4.7k':('MFS25F4K7B','108546'),
        '10k':('MFS25F10KB','108550'),'47k':('MFS25F47KB','108560'),
        '100k':('MFS25F100KB','108563'),'0R':('MFS25F0RB','108512'),
    }[value]
    add(ref,sheet,block,value,'Miniature1/4W axial metal film1%; jumper excepted',pn,'Akizuki '+code,pop,'R_AXIAL_P7.62',PASSIVE,[a,b],
        S['r']+' | '+A+code+'/',notes='Nonpolar,local pin1/2. Pitch7.62 chosen for3.3mm body. '+note)


add('J101',1,'ENTRY','MJ-179PH','Center-positive DC jack with unused switch contact','MJ-179PH','Akizuki106568','yes','MJ179PH_PLACEHOLDER',
    [(1,'CENTER'),(2,'SLEEVE'),(3,'SWITCH')],['VIN_RAW','GND','NC'],S['mjpage']+' | '+S['mjdraw'],'assumption',
    'PCB-stage HOLD: replace pad/slot geometry before layout. Logical1CENTER=VIN_RAW,2SLEEVE=GND,3SWITCH=NC approved by Claude. Claude visually verified outline/contact diagram2026-10-21: SWITCH touches SLEEVE with no plug. Confidence=assumption applies only to physical placeholder; logical connections are approved. Keep3 pads named1/2/3 with no claimed positions; do not use placeholder for layout. No further Akizuki PDF access attempts.')
add('F102',1,'ENTRY','3A hold/30V','Radial resettable PTC','MF-R300','Akizuki112630','yes','F_MFR300_P5.1',PASSIVE,['VIN_RAW','VIN_FUSED'],S['fuse'],notes='Nonpolar,local numbering.')
add('D103',1,'ENTRY','1N5822','Panjit series reverse-polarity Schottky','1N5822','Akizuki102229','yes','D_DO201AD_P15.24',DIODE,['VIN_PROT','VIN_FUSED'],S['d5822'],notes='Band=K1 atVIN_PROT; A2 atVIN_FUSED; heat clearance.')
add('J104',1,'ENTRY','POWER SWITCH','Header to off-board panel toggle','PH-1x40SG cut1x2','Akizuki100167','yes','HDR_1X2_P2.54',[(1,'VIN_PROT'),(2,'VM')],['VIN_PROT','VM'],A+'100167/',notes='Header pin order is design choice. Off-board switch excluded.')
add('D105',1,'ENTRY','P4KE15A','Panjit unidirectional TVS','P4KE15A','Akizuki129633','yes','D_DO41_P10.16',DIODE,['VM','GND'],S['tvs'],notes='Band=K1 atVM; A2 atGND. A suffix,not CA.')
cap('C106',1,'ENTRY','470uF/35V','VM','GND')
add('U107',1,'5V SUPPLY','M78AR05-1','1A switching regulator','M78AR05-1','Akizuki113536','yes','M78AR05_1_SIP3',[(1,'VIN'),(2,'GND'),(3,'VOUT')],['VM','GND','+5V'],S['m78'],notes='Maker p3 pin table verified. Drawing is BOTTOM VIEW; body-offset transcription pending. Max output capacitance470uF.')
cap('C108',1,'5V SUPPLY','100uF/35V','VM','GND')
cap('C109',1,'5V SUPPLY','100uF/35V','+5V','GND')
add('D110',1,'5V SUPPLY','1N5819','Wuxi Xuyang supply isolation Schottky','1N5819','Akizuki117244','yes','D_DO41_P10.16',DIODE,['VSYS','+5V'],S['d5819'],notes='Band=K1 atVSYS; A2 at+5V.')

PICO_NAMES='GP0 GP1 GND@3 GP2 GP3 GP4 GP5 GND@8 GP6 GP7 GP8 GP9 GND@13 GP10 GP11 GP12 GP13 GND@18 GP14 GP15 GP16 GP17 GND@23 GP18 GP19 GP20 GP21 GND@28 GP22 RUN GP26 GP27 AGND GP28 ADC_VREF 3V3_OUT 3V3_EN GND@38 VSYS VBUS'.split()
PICO_NETS='NC UART_RX GND HDD1_IN1 HDD1_IN2 HDD2_IN1 HDD2_IN2 GND HDD3_IN1 HDD3_IN2 HDD4_IN1 HDD4_IN2 GND NC NC NC NC GND ARM FAULT SLEEP MUX_S0 GND MUX_S1 NC NC NC GND NC NC VM_SENSE I_SENSE GND T_SENSE NC +3V3 NC GND VSYS NC'.split()
add('U201',2,'MCU','Raspberry Pi Pico','RP2040 module with two1x20 sockets','SC0915 + FHU-1x20SG x2','Akizuki116132; sockets105779','yes','RPI_PICO_SOCKET',list(enumerate(PICO_NAMES,1)),PICO_NETS,S['pico'],
    notes='All40 socket pins. AGND33=GND. GP25 onboard LED no socket pin. SWD pads excluded. Main datasheet retrieval failed3x (>10MB); official Pico1/Pico2 pinout used. Socket hole recommendation verified on store page.')
for ref in ['J202','J203']:
    add(ref,2,'SMARTNET','XH2P','Parallel SmartNet input/pass-through','B2B-XH-A(LF)(SN)','Akizuki112247','yes','JST_XH_B2B_2P_P2.50',[(1,'SIGNAL'),(2,'GND')],['SN_BUS','GND'],S['xh'],notes='SmartNet section2 gives no pin-order rule; task decision1signal,2GND; both parallel beforeR204.')
resistor('R204',2,'SMARTNET','1k','SN_BUS','SN_RX_IN')
resistor('R205',2,'SMARTNET','10k','SN_RX_IN','SN_PU')
add('D206',2,'SMARTNET','BAT43','Wuxi Xuyang pull-up back-feed blocking Schottky','BAT43','Akizuki113907','yes','D_DO35_P7.62',DIODE,['SN_PU','+3V3'],S['bat'],'assumption',
    'A2 at+3V3,K1/band atSN_PU per explicit task. Body verified on store page; lead limit0.55 for hole sizing unverified graphically.')
add('U207',2,'SMARTNET','74AHC1G125W5','Diodes single non-inverting tristate buffer','74AHC1G125W5-7','Akizuki117605','yes','SOT23_5_SOT25',[(1,'/OE'),(2,'A'),(3,'GND'),(4,'Y'),(5,'VCC')],['GND','SN_RX_IN','GND','UART_RX','+3V3'],S['buffer'],notes='DS35176 p2 verified; /OE low enables; W5=SOT25.')
cap('C208',2,'SMARTNET','100nF/50V','+3V3','GND')
resistor('R209',2,'VREF','47k','+3V3','VREF')
resistor('R210',2,'VREF','4.7k','VREF','GND',note='Initial4.7k; change to10k only after thermal tests per6.3. One divider common to4 carriers.')
cap('C211',2,'VREF','220nF/50V','VREF','GND')
resistor('R212',2,'STOP','1k','ARM','ARM_SW')
add('J213',2,'STOP','STOP SWITCH','Header to off-board maintained stop toggle','PH-1x40SG cut1x2','Akizuki100167','yes','HDR_1X2_P2.54',[(1,'ARM_SW'),(2,'SLEEP')],['ARM_SW','SLEEP'],A+'100167/',notes='OPEN stops4 channels. Off-board switch excluded.')
resistor('R214',2,'STOP','10k','SLEEP','GND')
resistor('R215',2,'FAULT','10k','+3V3','FAULT')

POL_PINS=list(enumerate('VM GND@2 IN1 IN2 PMODE SLEEP VREF CS FAULT IMODE OUT2 OUT1 GND@13 VIN'.split(),1))
for n in range(1,5):
    b=300+10*n
    add(f'U{b}',3,f'HDD{n}','Pololu4035 MODIFIED','DRV8874 carrier with two1x7 sockets','Pololu4035(md41a) + FHU-1x7SG x2','Sengoku EEHD-6U5X; socketsAkizuki105779','yes','POLOLU_4035_SOCKET',POL_PINS,
        ['NC','GND',f'HDD{n}_IN1',f'HDD{n}_IN2','+3V3','SLEEP','VREF',f'HDD{n}_CS','FAULT','NC',f'HDD{n}_OUT2',f'HDD{n}_OUT1','GND','VM'],S['pololu']+' | '+S['polpin'],
        notes='Pin order visually verified by Claude2026-10-21 on Pololu labelled top-view photo. Additional carrier terminals VM1=NC (unused protected supply access),IMODE10=NC (spec6.2 floating afterR4 removal) approved by Claude; bothGND tied. No logic-VCC pin. No specified connection changed. REQUIRED remove onboardR2(10k VREF-SLEEP),R4(20k IMODE-GND); keepR3(2.49k CS-GND). Numbering local CCW,not IC pin numbers.')
    cap(f'C{b+1}',3,f'HDD{n}','470uF/35V','VM','GND')
    cap(f'C{b+2}',3,f'HDD{n}','100nF/50V','VM','GND')
    add(f'J{b+3}',3,f'HDD{n}','VH2P','HDD voice-coil connector','B2P-VH(LF)(SN)','Akizuki112815','yes','JST_VH_B2P_P3.96',[(1,'OUT1'),(2,'OUT2')],[f'HDD{n}_OUT1',f'HDD{n}_OUT2'],S['vh'],notes='Task connection1=OUT1,2=OUT2; HDD coil and cable parts off-board.')

MUX_PINS=list(enumerate('Y0 Y2 Y Y3 Y1 /E VEE GND S1 S0 X3 X0 X X1 X2 VCC'.split(),1))
add('U401',4,'MUX','TC74HC4052AP','Dual4-channel analog-mux scaffold','TC74HC4052AP(F)','Marutsu; code unspecified in BOM','DNP','DIP16_W7.62_P2.54',MUX_PINS,
    'NTC1 NTC3 T_SENSE NTC4 NTC2 GND GND GND MUX_S1 MUX_S0 HDD4_CS_F HDD1_CS_F I_SENSE HDD2_CS_F HDD3_CS_F +3V3'.split(),S['mux'],
    notes='Maker0Y,2Y,Y-COM,3Y,1Y,INH,VEE,GND,B,A,3X,0X,X-COM,1X,2X,VCC mapped to names. S0=A10,S1=B9,/E=INH6 (HIGH disables). X=current,Y=temperature.')
cap('C402',4,'MUX','100nF/50V','+3V3','GND','DNP')
resistor('R403',4,'SMARTNET BYPASS','0R','SN_RX_IN','UART_RX','DNP','Populate only whenU207 omitted. DNP resistor still has2 distinct nets; not a wire in expected list.')
for n in range(1,5):
    b=400+10*n
    resistor(f'R{b+1}',4,f'OPTIONAL HDD{n}','100k',f'HDD{n}_CS',f'HDD{n}_CS_F','DNP')
    cap(f'C{b+1}',4,f'OPTIONAL HDD{n}','100nF/50V',f'HDD{n}_CS_F','GND','DNP')
    resistor(f'R{b+2}',4,f'OPTIONAL HDD{n}','10k','+3V3',f'NTC{n}','DNP')
    cap(f'C{b+2}',4,f'OPTIONAL HDD{n}','100nF/50V',f'NTC{n}','GND','DNP')
    add(f'J{b+3}',4,f'OPTIONAL HDD{n}','PH2P NTC','Connector to off-board103AT-2','B2B-PH-K-S(LF)(SN)','Akizuki112802','DNP','JST_PH_B2B_2P_P2.0',[(1,'SENSOR'),(2,'GND')],[f'NTC{n}','GND'],S['ph'],notes='NTC off-board. Supervisor decision low-sideNTC; open=full-scale,short=0. Connector1sensor,2GND.')
resistor('R451',4,'VM SENSE','100k','VM','VM_SENSE','DNP')
resistor('R452',4,'VM SENSE','10k','VM_SENSE','GND','DNP')
cap('C451',4,'VM SENSE','100nF/50V','VM_SENSE','GND','DNP')
for number,net in [(460,'VM'),(461,'+5V'),(462,'+3V3'),(463,'GND'),(464,'GND'),(465,'GND'),(466,'VREF'),(467,'SLEEP'),(468,'FAULT'),(471,'HDD1_CS'),(472,'HDD2_CS'),(473,'HDD3_CS'),(474,'HDD4_CS')]:
    add(f'TP{number}',4,'TEST POINTS',net,'Single through-hole test pad','Bare plated pad','N/A','yes','TP_THT_D2.5',[(1,'TP')],[net],'Task T1 test-point requirement','assumption','PCB copper/hole/silk only;populate=yes; no purchased loop.')


def main():
    paths=[ROOT/'parts.csv',ROOT/'netlist_expected.csv']
    if any(p.exists() for p in paths):
        raise SystemExit('Refusing to overwrite existing CSV files.')
    parts.sort(key=lambda r:(int(r['sheet']),int(''.join(c for c in r['ref'] if c.isdigit())),r['ref']))
    order={p['ref']:i for i,p in enumerate(parts)}
    nets.sort(key=lambda r:(order[r['ref']],int(r['pin_number'])))
    for path,rows,fields in [(paths[0],parts,COLS),(paths[1],nets,['net','ref','pin_number','pin_name'])]:
        with path.open('x',encoding='utf-8',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\n')
            writer.writeheader();writer.writerows(rows)
        print(f'CREATED {path.name}: {len(rows)} rows')
    print('POPULATE',dict(Counter(p['populate'] for p in parts)))
    print('CONFIDENCE',dict(Counter(p['confidence'] for p in parts)))
    print('NAMED_NETS',len({r['net'] for r in nets}-{'NC'}))
    print('NC_PINS',sum(r['net']=='NC' for r in nets))


if __name__=='__main__':
    main()
