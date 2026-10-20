# スマート・ネットワーク簡易版（v2）

<aside>
🎵

**SmartNet v0.3.5（Raspberry Pi Pico 専用）**　PC の MIDI ファイル → マスタ Pico → UART 1本（既定 **38400bps**、9600 も可）→ 各スレーブ（ステッピングモータ／PWM出力／ソレノイド／自作機）。通信が途絶えたら、スレーブは**ライブラリの責任で 0.5秒以内に全出力を停止**する。

</aside>

## 0. ファイル

[SmartNet.zip](SmartNet.zip)

ライブラリ本体（Arduino IDE →「スケッチ」→「ライブラリをインクルード」→「.ZIP形式のライブラリをインストール」）。examples と extras（play_mid.py・テンプレート）を含む。

[SmartNet_template.mid](SmartNet_template.mid)

Domino 用テンプレート（トラック1〜16 = ch1〜16、テンポ120・4/4 のみ。余計なイベントは入っていない）。

[SmartNet_test.mid](SmartNet_test.mid)

動作確認用 MIDI（トラック1：音階、2：和音 C→F、3：音階、5：ソレノイド用 60/62/64/65）。

## 1. 全体構成

```
PC ──USB── マスタ Pico ──UART(GP0 TX) 38400bps──┬── スレーブ Pico（ステッピング ch1,ch2）
 play_mid.py                                     ├── スレーブ Pico（PWM ch3,ch4）
 （トラック番号→ch）                             ├── スレーブ Pico（ソレノイド ch5）
                                                 └── 自作スレーブ（68000 等。ライブラリ不要・下の仕様で実装）
```

- マスタは一方向に送るだけ（スレーブは返信しない）。全スレーブが同じ線を聞き、自分が担当する ch だけ処理する。
- **MIDI ファイルのトラック番号 = ch 番号**（トラック1 → ch1 … トラック16 → ch16）。ファイル内の MIDI チャンネル設定は無視する。ドラムも普通のピアノロールトラックに書けばよい。
- ch はスレーブの「担当番号」。1台のスレーブが複数 ch を担当してよく、複数のスレーブが同じ ch を聞いてもよい。
- 通信速度は既定 38400bps。**全機器を同じ速度にすれば** 9600 等でもよい（`net.begin(9600)`）。

## 2. 通信回路（これだけ）

```
マスタ Pico                         スレーブ（各台）
  GP0 (TX) ──[100Ω]──┬──────────────── RX（Pico なら GP1）
                     │            3.3V ──[10kΩ]── RX（スレーブ側でプルアップ）
  GND ───────────────┴──────────────── GND
```

- 配線は **TX と GND の2本だけ**（JST XH 2ピンを推奨）。100Ω はマスタ側に1本（短絡・反射対策）。
- スレーブの RX は 10kΩ で 3.3V にプルアップ（ケーブルが抜けても RX が浮かず、ゴミを受けにくい）。
- 複数台はバス状に並列接続でよい（数台・数 m 程度まで）。
- **68000 など Pico 以外のスレーブ**：UART の **TTL レベル入力**（例：MC68681 / MC68901 の RxD 端子）に直接つなぐ。5V TTL 入力は VIH = 2.0V なので 3.3V 信号で受けられる。
    - RS-232C レベル（±12V、MAX232 等の外側）には**つながない**。
    - スレーブ側の RX が 5V にプルアップされている場合は、そのプルアップを外すか、5V トレラントなバッファ（74LVC1G17 等）を入れる（Pico の GP0 に 5V を加えないため）。
- 出力回路（モータドライバ・ソレノイド・FET など）は各スレーブで設計する。条件は「安全設計 ④」を守ること。

## 3. 安全設計（フェイルセーフ）

1. **リース方式**：スレーブは「最後に正しいフレームを受けてから 500ms」経つと全出力を停止。マスタは 100ms ごとにハートビートを送り続ける。
2. **出力はライブラリが所有**：`attach()` した出力と `addSafePin()` したピンは、タイムアウト・ALL_OFF・起動時に必ず安全状態へ。
3. **ウォッチドッグ**：`enableWatchdog()` でプログラムが固まったら自動リセット（リセット後は全出力 OFF から再開）。
4. **出力回路の条件（要件）**：MCU が起動中・リセット中・ピンが入力状態でも出力が OFF になるよう、ドライバ入力に**プルダウン（またはOFF側へのプル）抵抗**を入れる。
5. **状態の再同期（STATE）**：ノートオフが化けて失われても、50ms ごとの STATE 送信で鳴りっぱなしを自動修正。
6. ソレノイドは 1回の通電を最大 100ms に制限（ライブラリ内の絶対上限）。

## 4. 通信プロトコル仕様（自作スレーブ用・完全版）

ライブラリを使わないスレーブ（68000 など）は、この章だけで実装できる。

### 4.1 物理層

| 項目 | 値 |
| --- | --- |
| 方式 | 非同期シリアル（UART）、マスタ → スレーブの一方向 |
| 速度 | 38400bps（既定）。全機器を揃えれば 9600bps 等も可 |
| フォーマット | 8N1（データ 8bit、パリティなし、ストップ 1bit）、LSB ファースト |
| 論理レベル | 3.3V CMOS（アイドル = High） |
| 1バイトの時間 | 38400bps：約 0.26ms ／ 9600bps：約 1.04ms |

### 4.2 フレーム構造

```
[ステータス] [データ0] [データ1] … [CRC]
 1ccc nnnn    0xxxxxxx  0xxxxxxx    0xxxxxxx
```

- **ステータスバイト**：最上位ビットが 1（0x80〜0xFF）。`ccc` = コマンド番号（0〜7）、`nnnn` = ch − 1（ch1 → 0、ch16 → 15）。
- **データバイト**：0〜127（最上位ビット 0）。
- **CRC**：最後の1バイト。ステータス＋全データバイトに対する CRC-7/MMC（0〜127 なのでデータバイトと同じ形）。
- 0x80 以上のバイトを受けたら、**途中のフレームは捨てて新しいフレームを開始**する（ずれても次のフレームで必ず復帰）。
- フレームは連続して届く（間隔ゼロ）。フレーム間の無音時間に依存しないこと。

### 4.3 コマンド一覧

| ccc | 名前 | データ | 全長 | 意味 |
| --- | --- | --- | --- | --- |
| 0 | NOTE_OFF | note | 3 | その ch の note を止める |
| 1 | NOTE_ON | note, vel | 4 | note を鳴らす（vel = 1〜127）。**vel = 0 は NOTE_OFF と同じ** |
| 2 | STATE | n, (note, vel) × n | 3 + 2n | その ch で「今鳴っているべき音の全リスト」（n = 0〜8） |
| 3 | PARAM | id, hi7, lo7 | 5 | パラメータ。値 = hi7 × 128 + lo7（0〜16383） |
| 4 | CH_OFF | なし | 2 | その ch の全音を止める |
| 5, 6 | 予約 | — | — | 無視して次のステータスバイトを待つ |
| 7 | SYSTEM | なし | 2 | `nnnn` がシステム番号：0 = HEARTBEAT（0xF0）、1 = ALL_OFF（0xF1）。全スレーブ共通 |

PARAM の id：0〜119 は MIDI の CC 番号そのまま（7 = 音量、1 = モジュレーション等。CC の値は lo7 に入り hi7 = 0）。**id 127 = ピッチベンド**（8192 が中央。ライブラリでは −8192〜8191 に換算して渡す）。自作スレーブは不要な PARAM を無視してよい。

**予約済みの使い方**：id 11（CC11 Expression）= 出力の強さ（デューティ／パルス幅。0 = 最小、127 = 最大、既定 127）。id 16（CC16）= ステッピングモータの回転方向（0 = スレーブの既定に戻す、1〜63 = 正転、64〜127 = 逆転）。自作スレーブでモータを回す場合も同じ意味にそろえること。

### 4.4 CRC-7/MMC（C言語）

多項式 x⁷ + x³ + 1（0x09）、初期値 0、MSB ファースト、最終 XOR なし。チェック値：ASCII "123456789" → **0x75**。

```c
unsigned char crc7(const unsigned char *p, int n)
{
    unsigned char crc = 0;
    int i, k;
    for (i = 0; i < n; i++) {
        unsigned char b = p[i];
        for (k = 0; k < 8; k++) {
            unsigned char top = ((crc >> 6) ^ (b >> 7)) & 1;
            crc = (crc << 1) & 0x7F;
            if (top) crc ^= 0x09;
            b <<= 1;
        }
    }
    return crc;   /* 0〜127 */
}
```

（68000 で速くしたい場合は、この関数で 256 バイトの表を作り `crc = table[(crc << 1) ^ b]` としてもよい。）

### 4.5 受信処理（擬似コード）

```
buf[19], len = 0, need = 0

受信バイト b ごとに:
  if (b >= 0x80) {                 // ステータス → 新しいフレーム開始
      cmd = (b >> 4) & 7
      if (cmd == 5 || cmd == 6) { len = 0; return; }     // 予約は無視
      buf[0] = b; len = 1
      need = (cmd==0) ? 3 : (cmd==1) ? 4 : (cmd==3) ? 5 : (cmd==2) ? 0 : 2
      return
  }
  if (len == 0) return              // フレーム外のデータは捨てる
  buf[len++] = b
  if (cmd == 2 && len == 2) {      // STATE の n
      if (b > 8) { len = 0; return; }
      need = 3 + 2 * b
  }
  if (need != 0 && len == need) {
      if (crc7(buf, len - 1) == buf[len - 1]) フレーム実行(buf)
      else エラー数++
      len = 0
  }
```

### 4.6 スレーブの必須要件（MUST）

1. **タイムアウト**：「最後に正しいフレームを受けた時刻」を記録し、**500ms 以内**に何も来なければ全出力を OFF にして、鳴っている音のリストも空にする（300〜500ms を推奨）。正しいフレームとは「CRC が合った SYSTEM フレーム」または「CRC が合った、自分が担当する ch のフレーム」。
2. **ALL_OFF** を受けたら、全 ch の全出力を即 OFF。
3. **STATE** を受けたら、その ch の音のリストを STATE の内容に合わせる：リストにあって STATE にない音 → OFF、STATE にあってリストにない音 → ON（STATE の vel で）。すでに鳴っている音はそのまま（鳴らし直さない）。n = 0 なら全部 OFF。
4. 担当していない ch のフレーム、予約コマンド、CRC 不一致のフレームは何もせず捨てる。
5. 1 ch に同時に覚える音は最大 8 音。あふれたら最も古い音を OFF にして入れ替える（ライブラリと同じ動作）。単音しか出せない出力は「最後に ON になった音」を鳴らす。
6. 同じ音の NOTE_ON が重なったら鳴らし直し（新しい vel）、リストは1つのまま。
7. 起動直後は全出力 OFF。マスタの最初のフレームが来るまで何もしない。

### 4.7 マスタの送信タイミング

| 送信 | タイミング |
| --- | --- |
| ALL_OFF | 起動時に1回、PC からの信号が 500ms 途絶えたとき |
| HEARTBEAT | 100ms ごと（全スレーブ共通） |
| NOTE_ON / NOTE_OFF / PARAM / CH_OFF | 発生したらすぐ |
| STATE | 50ms ごとに1フレーム。音が鳴っている ch と最近変化した ch を順番に（変化した ch は2回） |

### 4.8 テストベクタ（16進）

| 内容 | バイト列 |
| --- | --- |
| ch1 NOTE_ON 60, vel 100 | `90 3C 64 55` |
| ch1 NOTE_OFF 60 | `80 3C 14` |
| ch2 STATE [60/100, 64/90] | `A1 02 3C 64 40 5A 77` |
| ch2 STATE（空） | `A1 00 2A` |
| ch3 CH_OFF | `C2 37` |
| ch1 PARAM CC7 = 100 | `B0 07 00 64 7D` |
| ch1 ピッチベンド中央 | `B0 7F 40 00 00` |
| HEARTBEAT | `F0 0E` |
| ALL_OFF | `F1 07` |

### 4.9 帯域と遅れ（目安）

- 38400bps：1秒に 3840 バイト。NOTE_ON 1つ 約 1.0ms、8音の和音でも最後の音まで約 8ms。
- 9600bps：1秒に 960 バイト。NOTE_ON 1つ 約 4.2ms、8音の和音で約 33ms のずれ。
- 待機中の負荷（HEARTBEAT＋STATE）は約 120 バイト／秒（38400bps で約 3%）。
- `play_mid.py` は再生前に「最も混む 100ms の送信量」を表示する（上限 = 速度 ÷ 100 バイト）。

## 5. MIDI ファイルの作り方と再生

### 5.1 Domino での作り方

1. `SmartNet_template.mid` を Domino で開く。
2. トラック1〜16 のピアノロールに音符を書く（トラック番号 = ch）。ステッピングモータの回転方向はそのトラックに CC16（Domino では「汎用1 / General Purpose 1」）を置く：1〜63 = 正転、64〜127 = 逆転、0 = 既定。デューティを Expression で変える設定のスレーブには CC11（エクスプレッション）を書く。ドラム・ソレノイドも普通のトラックに音の高さで書く（例：ソレノイド GP14〜17 = ノート 60/62/64/65）。
3. テンポ・拍子は Conductor トラックで変更してよい。音色（プログラムチェンジ）や Domino の MIDI チャンネル設定は**演奏には関係ない**（試聴用に自由に変えてよい）。
4. 「SMF 形式で保存」（フォーマット1）。
5. `python play_mid.py 曲.mid --check` で、トラック → ch の対応と音符数を確認してから再生する。

### 5.2 play_mid.py

```jsx
pip install pyserial                      （mac は pip3 / python3）
python play_mid.py 曲.mid                 ← マスタを自動で探して再生
python play_mid.py 曲.mid --loop          ← 無限ループ再生（Ctrl+C で停止）
python play_mid.py 曲.mid --loop 3        ← 3回くり返し
python play_mid.py 曲.mid --name stage1   ← 名前が stage1 のマスタで再生（マスタが複数のとき）
python play_mid.py 曲.mid --check         ← 確認だけ（トラック→ch 表と混雑チェック）
python play_mid.py --find                 ← つながっているマスタの一覧
python play_mid.py 曲.mid COM5            ← ポートを直接指定（mac: /dev/cu.usbmodem1101 など）
```

- **COM 番号を毎回調べなくてよい**：Master.ino の `net.setPcName(Serial, "SmartNet")` で付けた名前を手がかりに、USB につながった Pico（USB ID 2E8A）へ問い合わせてマスタを見つける。Windows・macOS・Linux 共通で動く。
- マスタが1台なら名前を気にしなくてよい。複数台なら別々の名前を付けて `--name` で選ぶ（名前は英数字16文字まで。空白・カンマ・日本語は不可）。
- Arduino IDE のシリアルモニタでマスタのポートを開いていると見つからない（閉じてから実行）。
- 問い合わせの中身：PC → マスタに SysEx `F0 7D 53 4E 3F F7`（7D = 教育・非商用用 ID）、マスタ → PC にテキスト1行 `SMARTNET,MASTER,0.3.3,名前`。演奏データには影響しない。
- **再生後の診断表示**：再生が終わると「PC が送った音 / マスタが受け取った音 / マスタがスレーブへ送った音」の数を表示する（状態の問い合わせ SysEx `F0 7D 53 4E 23 F7` → `SMARTNET,STAT,速度,受信バイト,受信ノート,送信ノート,鳴っている音`）。
- **ループ再生**：1周の長さは「最後のイベントを小節の終わりまで切り上げた長さ」（拍子は Conductor の最初の拍子記号、なければ 4/4）。時刻は最初の再生開始を基準に計算するので、何周しても遅れがたまらない。周の境目で念のため全 ch を停止する。--name 等と組み合わせ可。
- 指定したポートからマスタの返事がない場合は、送らずに止まる（スレーブのポートを指定してしまう事故を防ぐ。確認を省くなら `--force`）。
- フォーマット1：テンポ専用トラック（Conductor）を除いた **1番目のトラック = ch1**、2番目 = ch2 …（最大16）。
- フォーマット0（トラックが1つだけ）：ファイル内の MIDI チャンネルを ch として使う。
- 送るもの：ノートオン/オフ、CC、ピッチベンド。開始時・終了時・Ctrl+C で全 ch 停止。再生中は 100ms ごとに生存信号を送る（PC が止まるとマスタが 500ms で全停止）。
- マスタ側の速度を 9600 にした場合は、`play_mid.py` 先頭の `NET_BAUD` も 9600 にする（混雑チェック用）。

## 6. 関数リファレンス（Pico）

### 6.1 スレーブ：SmartSlave

```cpp
#include <SmartNet.h>
SmartSlave net(Serial1);          // Serial1 = GP0(TX)/GP1(RX)
SmartStepper motor1(2, 3, 4);     // STEP=GP2, DIR=GP3, EN=GP4

void setup() {
  net.attach(motor1, 1);          // motor1 は ch1 を演奏
  net.enableWatchdog(1000);
  if (!net.begin()) { /* 設定エラー（PWM スライスの重複など） */ }
}
void loop() { net.update(); }     // loop は止めずに回し続ける
```

| 関数 | 説明 |
| --- | --- |
| `SmartSlave net(Serial1)` | スレーブを作る |
| `bool begin(baud = 38400)` | 開始。false = 出力の設定エラーあり（その出力は動かない） |
| `update()` | loop で毎回呼ぶ（受信・タイムアウト・出力処理） |
| `attach(出力, ch)` | 出力を ch に割り当て（最大32個） |
| `listen(ch)` | 出力なしで ch を聞く（コールバックで自作処理する場合） |
| `addSafePin(pin, level)` | タイムアウト・停止時にそのピンを level に戻す（最大32本） |
| `onNoteOn(fn)` / `onNoteOff(fn)` | `fn(ch, note, vel)` / `fn(ch, note)` |
| `onAllOff(fn)` / `onParam(fn)` | 全停止時 / `fn(ch, id, value)`（ピッチベンドは id 127、−8192〜8191） |
| `setTimeout(ms)` | 停止までの時間（既定 500） |
| `enableWatchdog(ms)` | ウォッチドッグ（最大 8300ms） |
| `isConnected()` / `isListening(ch)` | 通信中か / その ch を聞いているか |
| `lastNote(ch)` / `lastVelocity(ch)` | 最後に ON になった音（なし = −1） |
| `isNoteOn(ch, note)` / `noteCount(ch)` / `noteAt(ch, i)` | 鳴っている音の確認 |
| `errorCount()` | CRC エラー等の数（配線チェックに使う） |

### 6.2 出力クラス

| クラス | 説明 |
| --- | --- |
| `SmartPwm(pin)` | ハードウェア PWM でその音の周波数を出す（単音・その ch の最後の音） |
| `SmartStepper(step, dir = −1, en = −1)` | ステッピング用（既定はデューティ 50%、新しい音ごとに DIR 反転、EN は演奏中 LOW）。`setDuty` 等も使える |
| `SmartSolenoid(pin, note, minMs = 10, maxMs = 30)` | note が来たら vel に応じた時間だけ ON（上限 100ms） |
| `SmartOutput` を継承 | 自作出力（`allOff()` の実装が必須） |

SmartPwm（SmartStepper も同じ）の設定：

| 関数 | 説明 |
| --- | --- |
| `setDuty(%)` / `setDuty(min, max)` | デューティ固定 / 強さ 1→min、127→max |
| `setPulseUs(µs)` / `setPulseUs(min, max)` | パルス幅固定 / 強さで変える（短いパルス用） |
| `setMaxDuty(%)` | デューティの上限（既定 50%）。パルス幅指定でも高い音でこれを超えない |
| `setDutyBy(SmartPwm::EXPRESSION)` | デューティ／パルス幅を velocity ではなく Expression（CC11）で変える。CC11 = 0 → min、127 → max。鳴っている音にもすぐ反映 |
| `setDutyCc(cc)` | 任意の CC で変える（255 = velocity に戻す） |
| `setTranspose(半音)` / `setMaxHz(Hz)` | 移調 / 周波数の上限（既定 20000Hz、下限 8Hz） |
| `ok()` / `playingNote()` | 設定が正しいか / 今鳴らしている音 |

SmartStepper だけの設定（回転方向）：

| 関数 | 説明 |
| --- | --- |
| `setDirection(SmartStepper::AUTO)` | 既定の方向。AUTO = 音が変わるたびに交互、FORWARD = DIR LOW、REVERSE = DIR HIGH |
| `setDirCc(cc)` | 方向を受け取る CC 番号（既定 16。MIDI で変えさせないなら 255） |
| `direction()` | 今の方向の設定 |
- MIDI の CC16：0 = 既定に戻す、1〜63 = 正転、64〜127 = 逆転。曲の途中でもすぐ反映（演奏中の音もその場で向きが変わる）。
- 停止（ALL_OFF・CH_OFF）・通信途絶のときは既定に戻る。前の曲の方向が次の曲に残らない。
- STATE では方向は再送されない。演奏中にスレーブが再起動した場合、次の CC16 までは既定の方向になる（ループ再生なら次の周の頭で戻る）。
- A4988 は DIR を STEP の立ち上がりより 200ns 以上前に確定させる必要があるが、音の始まりでは DIR を先に設定してから STEP を出すので問題ない。演奏中に向きを変えたときに 1 ステップずれることはある。
- velocity・Expression で duty を変えても、A4988 などのドライバでは音量はほとんど変わらない（電流は VREF で決まる）。
- Expression モードの既定値は 127（= max）。停止（ALL_OFF・CH_OFF）・通信途絶で 127 に戻る。STATE では再送されないので、曲の頭に CC11 を置いておくと確実（ループ再生でも毎周の頭で送られる）。

### 6.3 PWM スライスとピン（重要）

Pico の PWM は 2 本のピンが 1 つの「スライス」（同じ周波数）を共有する。**SmartPwm / SmartStepper は 1 スライスに 1 つだけ**。重なると `begin()` が false を返し、その出力は動かない。`analogWrite` も SmartPwm と同じスライスで使わないこと。

| スライス | ピン |
| --- | --- |
| 0 | GP0, GP1（UART で使用）, GP16, GP17 |
| 1 | GP2, GP3, GP18, GP19 |
| 2 | GP4, GP5, GP20, GP21 |
| 3 | GP6, GP7, GP22 |
| 4 | GP8, GP9 |
| 5 | GP10, GP11, GP26, GP27 |
| 6 | GP12, GP13, GP28 |
| 7 | GP14, GP15 |

GP25 はオンボード LED。GP23 / GP24 / GP29 は基板の端子に出ていない。

### 6.4 マスタ：SmartMaster

| 関数 | 説明 |
| --- | --- |
| `SmartMaster net(Serial1)` / `begin(baud = 38400)` | 開始（ALL_OFF を送る） |
| `update()` | loop で毎回（HEARTBEAT・STATE の送信） |
| `handleMidiByte(b)` | PC から来た MIDI バイトを渡す（ノート・CC・ピッチベンド。CC120/123 → CH_OFF） |
| `noteOn(ch, note, vel)` / `noteOff(ch, note)` | 直接送る |
| `allOff()` / `channelOff(ch)` | 全停止 / 1 ch 停止 |
| `sendParam(ch, id, value)` | PARAM を送る（value 0〜16383） |
| `setPcTimeout(ms)` | PC 途絶で全停止するまでの時間（既定 500） |
| `setPcName(Serial, "名前")` | PC から探すときの名前（play_mid.py の自動検出・`--name` 用） |
| `activeNotes()` | 今鳴らしている音の数（Master.ino ではこれで LED を点ける） |
| `pcNoteCount()` / `sentNoteCount()` | PC から受け取ったノートオンの数 / スレーブへ送った数 |

### 6.5 examples

| 名前 | 内容 |
| --- | --- |
| Master | USB の MIDI を受けて GP0 から送る。音を鳴らしている間 LED 点灯 |
| StepperSlave | motor1 = GP2/3/4（ch1）、motor2 = GP6/7/8（ch2）。設定エラー時は LED 高速点滅 |
| PwmSlave | GP10（ch3）短パルス 20〜200µs・上限10%、GP12（ch4）デューティ 5〜50% |
| SolenoidSlave | GP14〜17 = ノート 60/62/64/65（ch5） |
| CustomSlave | ch6〜8 を listen して analogWrite（GP18/20/22）、addSafePin の例 |

## 7. 組み立て・受け入れテスト

1. Arduino IDE に「Raspberry Pi Pico/RP2040（Earle Philhower 版）」ボードを入れ、ZIP ライブラリをインストール。
2. マスタに Master、スレーブに各 example を書き込み、通信回路（2本）をつなぐ。
3. `python play_mid.py --find` でマスタが見つかることを確認し、`python play_mid.py SmartNet_test.mid` で ch1〜3・5 が鳴ることを確認。
4. **途絶テスト**：演奏中に通信線を抜く → 0.5秒以内に全出力が止まること。挿し直すと次の音から再開すること。
5. **PC 停止テスト**：演奏中に play_mid.py を Ctrl+C／USB を抜く → 全停止すること。
6. `errorCount()` が増え続けないこと（増えるなら配線・GND・速度設定を確認）。

## 8. トラブルシューティング

| 症状 | 確認すること |
| --- | --- |
| マスタが見つからない | USB 接続、Master.ino の書き込み、シリアルモニタを閉じたか。だめならポートを直接指定 |
| 何も鳴らない | まず play_mid.py の診断表示とLEDで切り分け：マスタの LED が点かない → PC → マスタ（ポート・Master.ino の版）。マスタの LED は点くがスレーブの LED が消えている → マスタ → スレーブ（GP0 → GP1・GND・速度・ライブラリの版）。両方点くのに動かない → スレーブの ch・出力回路 |
| 一部の出力だけ動かない | `begin()` が false でないか（PWM スライスの重複） |
| 音が遅れる・もたつく | play_mid.py の混雑チェック、9600 なら 38400 にする |
| 鳴りっぱなし | 起こらない設計（STATE で修正、途絶で停止）。起きたら出力回路のプル抵抗を確認 |
| errorCount が増える | ノイズ・配線長・プルアップ抵抗・5V 混在 |
| 68000 スレーブが反応しない | 4.8 のテストベクタを PC から直接送って受信処理を単体確認 |

## 9. 検証状況

- ライブラリは PC 上の模擬環境でテスト済み（全項目合格）：周波数精度（440.002Hz）、パルス幅・デューティ上限、ソレノイド時間、ノートオフ欠落からの STATE 復帰、2% のビット化け耐性、途絶 → 約 475ms で全停止、再接続、ゴミデータ無視、38400bps で混雑なし。PC 側の自動検出（1台・複数台・名前指定・使用中ポート）と再生データの到達（38音すべて）も疑似マスタで確認済み。
- **実機（Pico・68000 スレーブ）ではまだ動作確認していない**。最初は 7 章の手順で確認すること。