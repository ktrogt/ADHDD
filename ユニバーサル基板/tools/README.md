# Perfboard tool — T6 interface v1 (2026-10-22)

Python 3.10+、標準ライブラリだけで動く配置・配線・検証ツール。**入力した物理モデルの接続を検証するもので、仮フットプリントの実物適合を保証しない。** 開発用デモを製作用配線図として使わない。

## T5 / T7 向けの先行公開インターフェース

JSON は UTF-8、`schema_version: 1`。未知のルール種類や不正な入力は黙って無視せず入力エラーにする。座標はすべて TOP view：列 A…Z, AA…、行 1…、左上 A1。回転は TOP view で時計回り。距離の単位は明記する。

### board.json

```json
{"schema_version":1,"columns":60,"rows":45,"pitch_mm":2.54,
 "type":"single_sided_independent","edge_margin_holes":0,
 "body_clearance_mm":0.5,
 "keepouts":[{"id":"mount","from":"A1","to":"B2"}]}
```

`type`: `single_sided_independent` / `double_sided_plated`。独立ランド専用で、ストリップ基板は非対応。基板外形は最外穴から半ピッチ外。keepout は両端を含む穴の長方形（その穴の半ピッチ外まで部品も禁止）。追加の `width_mm`, `height_mm`, `name`, `provisional`, `notes` はメタデータ。

### footprints.json / T5 footprints_ub.json

```json
{"schema_version":1,"footprints":{
 "POLOLU_4035_SOCKET":{
   "pins":[{"number":"1","name":"VM","dx":0,"dy":0},
           {"number":"2","name":"GND@2","dx":0,"dy":1},
           {"number":"8","name":"VIN","dx":5,"dy":0}],
   "body_mm":{"x":-1.3,"y":-1.3,"width":15.3,"height":18.0},
   "height_mm":12.0,"hot":true,
   "polarity":{"pin":"1","label":"VM"},"provisional":true,
   "notes":"Example only: supply all 14 pins in the actual footprint"
 }}}
```

`dx,dy`: **整数の穴オフセット**。`number,name` は文字列で footprint 内それぞれ一意。pin 1（原点）は `dx=dy=0`。`body_mm`: 原点からの TOP view 外形の長方形。`height_mm >= 0`, `hot` boolean、`polarity` は任意。実測待ちは `provisional:true` と理由・出典を `notes` / `sources` に残す。電気的なピン名は `parts.csv` と完全一致（例 `GND@2`）。リード径・穴径などの追加属性は保存するが機械適合の判定には使わない。

### placement.json

```json
{"schema_version":1,"parts":{
 "U310":{"footprint":"POLOLU_4035_SOCKET","hole":"K12",
         "rotation":0,"locked":true,"value":"Pololu #4035"}
}}
```

1 ref に 1 footprint が基本。別々のソケットにも対応するため、`parts` のキーを `U310_L` / `U310_R` とし、各要素に `ref:"U310"` を指定できる。この場合も `pins[].number/name` は**元のモジュール全体の番号・名前**を使う。body overlap はソケットごとに判定するので、モジュール全体の占有領域が必要なら 2×7 の単一 footprint を推奨。`pin_map` は任意の footprint pin number → `{number,name}` 対応（同じソケット形状を再利用する場合）。同一の電気 pin を複数の物理位置に作ることは不正。

### netlist.csv

既存 `基板/netlist_expected.csv` と同じ `net,ref,pin_number,pin_name`。`NC` は一つずつ独立で、NC 同士も接続禁止。デモでは populate=yes の部品を選び、足場回路を除外し、削減した probe point のみ残す。Pico の開放 GPIO は NC に変更し、変更の一覧をデモの scope 文書に残す。正本 CSV は変更しない。

### wiring.json

```json
{"schema_version":1,"conductors":[
 {"id":"W001","net":"VM","kind":"bare","side":"bottom",
  "path":["C3","H3","H5"],"gauge":"AWG20",
  "type":"tinned copper","colour":"red","locked":false}
]}
```

`kind`: `bare` / `bridge` / `jumper`。bare は穴グリッド上の直交線、bridge は隣接 2 穴だけ。`side` は `top` / `bottom`、bare/bridge の省略時は bottom、jumper は top。単面板の bare/bridge は bottom だけ。jumper は絶縁され、**両端だけ**で接続（中間 path 点は曲がり位置）。全種類の端末は穴へ通し裏面にはんだ付け。bare/bridge は通過する全穴のランドに接触するという保守的モデル。同じ面の露出線同士は交差・重なり・接触すれば必ず導通。両面スルーホール板は上下ランドが全穴で導通。ジャンパー途中の交差は導通しない。線の太さによる近接短絡は rules のクリアランスで別途判定する。

### design_rules.json — T7 generic rule engine

```json
{"schema_version":1,
 "groups":{"drivers":["U310","U320","U330","U340"],"caps":["C312","C322","C332","C342"]},
 "net_classes":{"power":["VM","GND","+5V","+3V3","VSYS"]},
 "router":{"power_nets":["VM","GND"],"power_gauge":"AWG20","signal_gauge":"AWG26","bend_penalty":0.4},
 "weights":{"wire_mm":1,"jumpers":20,"bridges":1,"crossings":2,"area_mm2":0.01,"error":100000,"warning":1000},
 "rules":[
  {"id":"heat","type":"min_part_distance","a":["U310"],"b":["C312"],"min_mm":3,"severity":"warning"},
  {"id":"local-cap","type":"near_pin","parts":["C312"],"pin":"U310.VIN","max_holes":3,"severity":"error"},
  {"id":"vref-length","type":"max_net_length","net":"VREF","max_mm":200,"severity":"warning"},
  {"id":"branch","type":"max_branch_length","net":"VM","from":"J104.VM","to":["U310.VIN"],"max_mm":150,"severity":"warning"},
  {"id":"quiet","type":"net_clearance","a":["VREF"],"b":["HDD1_OUT1","HDD1_OUT2"],"min_holes":2,"severity":"error"},
  {"id":"usb","type":"edge","parts":["U201"],"edge":"top","max_holes":2,"severity":"warning"},
  {"id":"star","type":"star","net":"VREF","root":"R217.P2","targets":["U310.VREF","U320.VREF"],"severity":"warning"},
  {"id":"wire","type":"wire_gauge","nets":["VM","GND"],"max_awg":20,"current_a":2.6,"min_area_mm2":0.5,"severity":"error"}
 ]}
```

`a,b,parts,nets,targets,to` は配列。part/net selector は正確な名前・glob (`U3*`)・`@group` / `@net_class`。pin は `ref.pin_name` または `ref.#number`、hole は `K12`。距離はユークリッド、部品間は外形間、near_pin は部品の最寄り pin、edge は外形から基板端。max_branch_length は**実配線の最短経路**、到達不能は違反。star は root を除いた導体グラフで target が互いにつながらない厳格な星形（trunk は別の方針なので star を指定しない）。wire_gauge は数値 AWG 上限、導体断面積下限、任意の `ampacity_a_per_mm2` × current を明示ルールとして検査し、汎用の許容電流を推定しない。すべてのルールで `severity`: error / warning / info、`enabled:false` 可。未定値を 0 で埋めない。未知 selector、未知 pin、未対応 type は入力エラー。

正式な JSON Schema は `schemas/`。CSV の制約は `schemas/netlist.schema.md`。実行時は標準ライブラリの明示的な検証を使う（汎用 JSON Schema ライブラリは不要）。

## CLI

リポジトリのルートで実行する例。`python` が PATH にない環境では、BRIEF に書かれた Python 実行ファイルを使う。

```powershell
python ユニバーサル基板/tools/ub.py selftest
python ユニバーサル基板/tools/ub.py demo --project ユニバーサル基板/tools/demo
python ユニバーサル基板/tools/ub.py verify --project ユニバーサル基板/tools/demo
python ユニバーサル基板/tools/ub.py metrics --project ユニバーサル基板/tools/demo
python ユニバーサル基板/tools/ub.py optimize --project ユニバーサル基板/tools/demo --seed 6 --iterations 500
python ユニバーサル基板/tools/ub.py route --project ユニバーサル基板/tools/demo
python ユニバーサル基板/tools/ub.py render --project ユニバーサル基板/tools/demo --scale 2 --tiles
python ユニバーサル基板/tools/ub.py wirelist --project ユニバーサル基板/tools/demo
python ユニバーサル基板/tools/ub.py continuity --project ユニバーサル基板/tools/demo
python ユニバーサル基板/tools/release_check.py
```

`all` は route → verify/metrics → SVG → 両 CSV。`demo` は暫定入力を作り直してから全工程を実行する。**demo を編集した場合、再生成で変更を失うので別の project を使う。** `route` は project/wiring.json を生成し直す。locked=true は保存し、`--keep-all` なら既存線をすべて保存する。optimize は元の placement.json を変更せず `placement.optimized.json` を出す。

全コマンド共通：`--out <dir>`（既定 project/out）、`--rules <file>`、`--footprints <file>`、`--placement <file>`、`--wiring <file>`。例えば最適化結果は `route --placement project/placement.optimized.json` で評価し、その後の verify/render にも同じ override を渡す。出力 wiring は project/wiring.json に書くため、比較する候補は別 project に分ける。render の `--annotate-wires` は線番号を加えるが、密集図には不向き。

終了コード：0=指定した検査で error なし（仮寸法 warning は許す）、1=検証不合格、2=不正入力。render/wirelist/continuity はデータの書き出しで、製作許可ではない。必ず同じ入力の report.json を確認する。

出力：`report.json`（DRC・LVS・抽出接続・ルールの PASS/FAIL/UNCHECKED）、`netlist_actual.csv`、`metrics.json`、`summary.txt`、`top.svg` / `bottom.svg` / `overlay.svg`、`wirelist.csv`、`continuity.csv`。SVG は mm 単位。1:1 デモは 234.4×189.7 mm で A4 横の印刷可能域 277×190 mm に収まる。印刷時は「実際のサイズ」、20 mm の校正線で確認する。2:1 の A4 分割は各 view 4 ページ。`from_hole,to_hole` は常に TOP の穴名。

## 接続検証の根拠

穴の座標を union-find（同じ導通グループにまとめる処理）に入れ、各導体の接触穴を結ぶ。線の net 名は接続を作らない。絶縁ジャンパーは端だけ、露出線は通過する全穴を接続し、交差点も同じ穴として結ぶ。抽出したグループを独立した netlist_actual.csv にし、正本の `基板/compare_netlist.py` を import してピン名・物理番号・ネット名・接続グループを照合する。同じネット名を別々の切れた線に書いても open を検出する。

追加の検査で、NC への短い行き止まり線、ピンのない浮遊配線、別ネットの裸線の重なり、未知のネット名、同じ穴のピン衝突も不合格にする。両面スルーホール板でも、上下に逃がした露出線が同じ穴を通れば短絡する。

これは**指定された理想導体モデルの検証**。部品内部の抵抗・ダイオード・モジュール内の GND 接続などは導通に含めず、各端子を基板側で結ぶ。NC は「ホスト基板から未接続」。実物のはんだ不良、線の浮き、リードの曲がり、はんだ玉、未知の変換基板内部パターンは実測が必要。

## T5・T7 の接続

T5 の実ファイル（2026-10-22）は schema_version が文字列 `"1.0"`、外形の縦寸法が `depth` だった。loader は 1 / height に読み替え、元の情報を保持する。`polarity_mark` は最初のピンのマークに変換。未確認の機械適合は provisional warning に残す。

`extra_pads` は `{physical_pin,dx,dy,net:"NC"}` の配列。未使用中央ピン・予約穴を電気ネットリストに足さず、占有と配線禁止を検査し、SVG に × を描く。`populate:false` でも保守的に予約する。`requires_Claude_approval:true` の代替部品は error を出す。Claude が承認した場合だけ配置要素に `substitution_approved:true` を記録できる。承認は loader で推定しない。

```powershell
python ユニバーサル基板/tools/import_t5.py --project ユニバーサル基板/tools/demo --footprints ユニバーサル基板/footprints_ub.json --out ユニバーサル基板/tools/demo/t5-proposal
python ユニバーサル基板/tools/ub.py verify --project ユニバーサル基板/tools/demo --rules ユニバーサル基板/design_rules_t6_subset.json --out ユニバーサル基板/tools/demo/out/t7-subset-audit
python ユニバーサル基板/tools/ub.py verify --project ユニバーサル基板/tools/demo --rules ユニバーサル基板/design_rules.json --out ユニバーサル基板/tools/demo/out/t7-audit
```

T5 import は ref_to_type を使い、全論理ピンの番号と名前が一致する場合だけ別 project を作る。以前の配線は破棄した空の wiring とする。実寸法を入れると以前の配置は衝突しうるため、import 成功は配置合格を意味しない。`demo/t5-proposal/` はその実例で、承認待ち・外形重なり・未配線の不合格が意図どおり出る。

T7 は v1 の部分版と、`adhdd-perfboard-rules/1.0` の全版を読める。部分版の `uncovered_rule_ids` / `partially_covered_rule_ids` は UNCHECKED の error として残す。全版で対応するのは Manhattan pin 距離、外形距離、実経路の最短距離、分岐間共有のない star、group、同方向、部品の並び、ジャンパー数。物理 feature のアクセス、線表面間クリアランス、枝別電圧降下、オフボード配線、取付金物、組立・実測、スコープ承認は未検査として残す。`placement.nodes` に `{node_name:"穴名"}` を書けるが、現在はアンカーピンの穴と同じ場合だけ扱う。T7 の枝内共有は許し、枝同士は root 以外でつながらないことを確認する。

## ルーター・最適化・指標の使い方

A* は座標に加えて進行方向を状態に持ち、長さと bend_penalty で直進を優先する。他ネットの端子・NC・予約穴・既存露出線を避け、VM/GND を先に木状に配線する。`router.trunks` に `{id,net,path,gauge}` を指定すれば太い幹線を先に固定できる。`power_roots` は配線開始点と電源経路の計測開始点。詰まると絶縁線に切り替える。電源の隣接穴も bare とし、断面積がわからない solder bridge に AWG を割り当てない。仮デモで電源線が長いのは初期配置の影響で、最適配置の主張ではない。

スコアは wire_mm×総長 + jumpers×本数 + bridges×数 + crossings×交差 + area_mm2×外接面積 + severity ごとの重み×違反数。T7 の重み付き・辞書式の正式ランキングとは別物で、T7 全版の生の重みと priority は findings に保持する。crossings はジャンパーと露出線の投影で交差する segment pair の数（曲がり点で重複しうる）。

最適化は seed 固定の焼きなまし。配置可能な移動・90°回転を試し、Manhattan MST（全端子を結ぶ短い木）の長さ推定とルール違反を下げる。locked 部品と、locked 配線に触れる部品は動かさない。外形・keepout・error 級の配置ルールは破らない。最終候補の比較には再配線後の metrics.score を使う。推定値の改善だけで実配線の改善は保証しない。

## 検証記録・2026-10-22（T6）

自動検証の正確な結果は `verification_results.json`、個々のテストは `selftest.log`。49 テスト PASS。意図的な短絡・断線・交差、NC の行き止まり線、追加 NC パッド、同じ名前で離れた配線、誤ピン番号、keepout、両面板の穴短絡、locked 配線、ジャンパーへの退避、ルーターと最適化の再現性を検査した。故障例は `fixtures/faults/`。`--wiring .../wiring.valid.json` では合格する。

暫定デモは 52 部品、184 ピン、37 ネット、27 NC。LVS PASS、DRC error 0、仮フットプリント warning 52。配線 120 本＝bare 62 本、bridge 1 個、jumper 57 本。長さ bare 1402.08 mm、bridge 2.54 mm、jumper 3360.42 mm、合計 4765.04 mm。外接占有面積 14481.449 mm²（仮基板面積の 83.134%）、投影交差 segment pair 316、既定 score 58682.854。手順 CSV は 120 行、導通試験は 1694 行。電源 VM→4 driver VIN は 124.46–175.26 mm。GND→driver は metrics.json に個別記載。

500 回・seed=6 の配置最適化例は `demo/placement.optimized.json` と `demo/out/optimization.json`。推定配線長 4361.18→4320.54 mm、固定 Pico/Pololu は不変。暫定の初期デモ自体は最適化結果に置き換えていない。

T7 全版での同じデモは LVS PASS / 総合 FAIL。全版 79 ルール中、PASS 10、FAIL 31、UNCHECKED 38。部分版も PASS 32、FAIL 64 に加え残条件 UNCHECKED 71。**デモが正しく接続することと、製作条件に合格することは別の判定。**

目視確認：Chrome で TOP と BOTTOM の SVG を開いた。TOP は Pico が左上、4 driver が下側で、部品記号・穴座標・値一覧を読めた。上端の説明と列名、校正線と値一覧の見出しの重なりを直した。小部品・probe のラベルは引出線でずらした。BOTTOM は Pico が右、列は BH…A の鏡像、赤/黒の露出電源線と破線の絶縁ジャンパーを区別できた。上部の配線は密で、絶縁線の投影が重なる箇所がある。実際の重ね方は未設計。18 SVG を XML として読み込み、1:1 の A4 寸法と裏面の反転も機械検査した。実機の印刷寸法・はんだ作業性は未確認。

観測した事実：コードのテスト、機械的な LVS/DRC の結果、ブラウザーでの図の見え方。推測・仮定：基板の機械的な適合、仮外形・変換基板・ジャックの端子位置、配線の立体的な干渉、冷却・ノイズ・許容電流の実機性能。

## 既知の制限

- 独立ランド限定。ストリップ基板・内部導体・導電性金物・部品内部パターンは未対応。
- 裸線は中心線上の接触を証明する。太さ、ランド外径、部品の露出リード、はんだ盛りによる近接接触には別の表面クリアランス検査と実物確認が要る。
- ジャンパーは投影線だけ。線の高さ、余長、端末のむき長、束の厚さ、部品への乗り上げを表さない。
- max_branch_length はグラフの最短経路。並列の不要な長い迂回線を排除する正式な枝別上限の証明には枝注釈が要る。T7 の残条件として未検査を残す。
- 最適化・自動配線は貪欲な木を初期値とするので、大域最適やジャンパー数の最少は保証しない。既定のルーターは star を検査するだけ。下記の追加オプションで指定した star は、枝の分離を検証してから出力する。
- 導通 CSV は電源 OFF・コンデンサ放電済みの**部品を付ける前の配線だけの基板**用。部品を付けると半導体・抵抗・コンデンサを通じた導通があるので、そのままブザー判定しない。
- T5 案・T7 条件の承認と実機確認は Claude の担当。今回のツール作業で部品の代替を採用したり、製作用配置を確定したりしていない。

作業範囲の指示に従い、引き継ぎ・決定・未決事項はこの README に記録した。正本の README / 作業記録 / 仕様書 / 部品 / ネットリストは編集していない。

## Claude v0.2 対応の追加（2026-10-22）

今回の変更範囲は tools/ と、Claude が明示的に編集を許可した共有 `ユニバーサル基板/board.json`。candidates/、design_rules*.json、footprints_ub.json、netlist_ub.csv は読み取りのみ。

### 実外形と格子原点

```json
{"schema_version":1,"columns":55,"rows":40,"pitch_mm":2.54,
 "outline_mm":{"width":155.0,"height":114.0},
 "grid_origin_mm":{"x":8.92,"y":7.47},
 "body_edge_margin_mm":1.0}
```

`grid_origin_mm` は TOP view で物理基板左上から A1 の中心まで。`outline_mm` を指定すると BODY_OFFBOARD は実外形から `body_edge_margin_mm`（既定 1.0 mm）だけ内側で判定する。部品の内部座標は従来どおり A1 基準なので、配置・配線の穴名は変わらない。穴・NC・予約穴・角の矩形 keepout の検査も維持する。`edge_margin_holes` は使用可能な穴を制限する。

`outline_mm` のない従来入力は従来どおり半ピッチ外側を基板端とする。旧 `width_mm` / `height_mm` や原点メタデータだけでは意味を切り替えない。実外形を使う入力では `outline_mm` が基準値となる。SVG の基板外形と裏面の反転軸もこの外形を使い、取付穴は図示する。取付金物の実際の占有空間は、明示 keepout と別途 M02 の確認が必要。

共有 board.json は 104708 の 155×114 mm と 55×40 穴を反映済み。原点は `(155−54×2.54)/2=8.92 mm`、`(114−39×2.54)/2=7.47 mm`。**T5 の中央配置からの計算値で、独立した寸法基準・製造公差を確認した値ではない。** 出典の継承元は `参考/調査記録/14_2026-10-22_ユニバーサル基板の部品と基板.md` と `board_options.csv` の AK104708 行。共有 JSON に根拠を記録した。

候補の古い board.json を変更せずに使うには、追加した `--board` を渡す。

```powershell
python ユニバーサル基板/tools/ub.py verify --project ユニバーサル基板/candidates/L1 --board ユニバーサル基板/board.json --rules ユニバーサル基板/design_rules_v0.2.json --rules-weights --out ユニバーサル基板/tools/_check/L1
```

### on_edge と accessible

T7 `on_edge.params.reference` は `board_edge`（省略時）/ `physical_outline` / `grid_boundary`。前二者は実外形（指定がなければ旧基板端）。`grid_boundary` は使用可能な最外行・最外列の穴中心を結ぶ線分を使う。edge_margin_holes と keepout で完全に使えなくなった外周行・列を除き、角の使用禁止穴も線分の端から除く。穴の半ピッチや実基板端までの距離には置き換えない。

距離は `feature` の宣言点から許可した N/E/S/W 線分までのユークリッド距離。footprint の `features[feature].x_mm/y_mm` を回転・移動して使う。未宣言のコネクタ端面を部品外形の中心から推定しない。未宣言部分は部品別に UNCHECKED。既存の canonical `edge` ルールの意味は変更していない。

M06 の `approach_by_part` は part ID、次いで論理 ref で引き、なければ従来の `approach` を使う。XH とヘッダは top、J101 は outward として記録する。ただし、現在の footprint にはプラグ・ラッチの完全な立体的占有領域と線の高さがないので、M06 は方向別の理由を付けた UNCHECKED。方向の推定による FAIL は出さない。この追加項目のない旧 accessible の判定は維持する。

on_edge で「一部の端面は未宣言、別の部品で距離を超過」という場合は、ルールを FAIL とし `unchecked_findings` も残す。未知の部分が既知の違反を隠さないため。

### T7 の重み付き採点と比較タプル

T7 全版を読むと自動で表示する。`--rules-weights` でも表示できる。既存の `passed`、終了コード、`metrics.score` は維持し、追加フィールドで比較する。従って UNCHECKED のため従来表示が FAIL の候補でも、比較タプルでコア DRC / hard FAIL が 0 の場合がある。

`comparison_tuple` の順番は次のとおり。

```text
(LVS ok, core DRC errors, hard FAIL count, jumpers, soft penalty, bends, total wire mm)
```

最初は true が良く、それ以外は小さい方が良い。全項目を昇順で比較したい場合は `lexicographic_sort_key` を使う（先頭を LVS PASS=0 / FAIL=1 に変換済み）。`comparison_tuple_fields` と `comparison_directions` も metrics.json に入る。

- core DRC errors：RULE: / LVS: 以外の error finding 数。既存の短絡・占有・外形・配線・承認待ちなどの検査を含む。
- hard FAIL count：実際に FAIL が出た hard ルールの **ID 数**。同じルールで 4 部品が超過しても 1。個々の finding は report.json にすべて残す。
- hard UNCHECKED：失敗・error としてタプルに加算しない。`unchecked_hard_rules` に理由を一覧化。実測できた FAIL と未知の部分が併存するルールは `hard_failed_rule_ids` に数え、追加の不明部分を `partially_unchecked_hard_rules` に分ける。
- soft penalty：T7 の weight を使い、数値条件は原子ごとに `weight × max(0, violation/bound)` を合計。下限は不足、上限は超過。bound=0 は分母 1。真偽条件は weight。UNCHECKED の未知部分は 0。`t7_soft_penalty_by_rule` に内訳、`unchecked_soft_rule_ids` に未検査条件、`soft_penalty_complete` に完全性を残す。既知の部分違反の罰点は保持する。
- bends：導体ごとの方向変化数。一直線上に中間穴が複数書かれていても曲がりには数えない。ジャンパーの投影経路を含む。

`ranking_pass` は LVS、コア DRC、既知の hard 条件についての合格。未検査の機械・電流・実装条件まで合格したという意味にはしない。

### 階層スターの自動配線（任意指定）

既定の配線動作は維持。rules の router に次を加えると、既存の star ルールを使って配線できる。全版の G01/G02/V01 をファイル外で変更せず試す場合は、読み込んだ rules のコピーに追加する。

```json
{"router":{"star_rule_ids":["G01","G02","V01"],
           "power_gauge":"AWG20","signal_gauge":"AWG26"}}
```

canonical v1 の star にも対応。ルールと独立して記述するなら `router.stars:[{id,net,root,branches:[{id,endpoints:[pin_or_node]}]}]`。`root` / endpoints は穴名、ピン名、`ref.#number` / T7 の `ref.number`、`$node` を扱う。named node は rules.nodes と placement.nodes の両方で宣言し、アンカーピンと同じ穴に置く。

端点同士を結ぶ各配線が、宣言した端点以外で他の枝に触れないよう予約する。裸線の A* を優先し、行き止まりでは絶縁線を使う。GND_ENTRY→GND_LOGIC のように親の枝の終端を子のハブにできる。生成後に LVS と指定した star の枝分離を検査し、矛盾した指定は配線を保存する前に拒否する。全 star は最上位 root が一つの階層にする。

制限：選んだ star ネットに保存対象の配線・幹線がある場合は拒否する。他ネットの locked 配線は維持できる。star ルールに列挙していない同ネットの端子は最上位ハブへの独立した枝にするので、静かな GND へ戻すべき端子は明示的に枝へ含める。枝内の幹線共有は現在最適化しない。枝の分離を優先するためジャンパーが増える場合があり、ジャンパー最少の保証はない。

L1 の配置だけを読み、既存配線を空にした別データで G01/G02/V01 を使う実行も確認した。LVS PASS、3 star ルールすべて PASS、star の導体 47 本。生成結果は `tools/_check/star_route_example/`。候補 L1 のファイルには書いていない。全体のジャンパーは 80 本で、既存候補の代わりに採用する判断はしていない。

### v0.2 での候補の読み取り検証

再現用コマンドは `python ユニバーサル基板/tools/audit_candidates.py`。出力は `tools/_check/`。入力ハッシュと検証前後の一致を `candidate_comparison.json` に保存する。共有実外形と v0.2 rules を override し、候補の配置・配線・部品・ネットリストを変更しない。

| 候補 | LVS | core DRC | hard FAIL IDs | jumpers | soft penalty | bends | 総長 mm |
|---|---|---:|---:|---:|---:|---:|---:|
| L1 | PASS | 0 | 0 | 39 | 243.356546 | 84 | 3201.762 |
| L2 | PASS | 0 | 1 | 41 | 193.661190 | 106 | 3591.560 |

このスナップショットでは L1 の BODY_OFFBOARD は旧境界の 1→実外形の 0。L2 の既知の hard 違反は M08 のコイルコネクタ 4 個：格子端から J313=3、J323=11、J333=11、J343=3 穴（上限 2）。M07 / M09 は両候補で PASS。M08 のヘッダ J104 / J213 は端面座標が未宣言なので、L1 では UNCHECKED、L2 では既知 FAIL に付随する未検査部分。hard UNCHECKED は L1=23 ルール、L2=22 ルール＋M08 の部分未検査。

追加後の selftest は 71 件 PASS。実外形・余白・keepout 保持、旧メタデータの互換、feature の回転、格子端と実外形の使い分け、方向別 UNCHECKED、重み付き上限/下限、未検査除外、曲がり数、平坦/階層 star、矛盾の拒否、再現性を含む。初期デモの従来ルーター再生成と 18 SVG の検査も PASS。候補は今後更新されるため、比較には同じ入力・同じ共有 board/rules のハッシュを使う。
