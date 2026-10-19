# SPC7110 解壓器

以 Python 實現的 SPC7110：其解壓器涵蓋全部三種輸出模式，逐位元組與 snes9x 保持一致；主機存取它所經的暫存器則以 ares 為準。

[English](README.md) | [日本語](README.ja.md) | [简体中文](README.zh-Hans.md) | 繁體中文（香港）

[![CI](https://github.com/gufranco/snes-spc7110-python/actions/workflows/ci.yml/badge.svg)](https://github.com/gufranco/snes-spc7110-python/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/gufranco/snes-spc7110-python)](https://github.com/gufranco/snes-spc7110-python/releases)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

**3** 種模式，**200** 條生成的數據流共 **102,400** 位元組，以及 **619** 條卡帶數據流共 **316,928** 位元組，均與參考實現比對，**619** 條卡帶數據流及 **231** 個暫存器驅動的案例經由暫存器讀取並與 ares 比對，**0** 處分歧，**780** 項測試，**100%** 語句與分支覆蓋率，無任何依賴

```python
import spc7110

part = spc7110.Chip("spc7110")
started = part.decompress(bytes(range(256)), "4bpp")

print(started.read(8).hex(" "))
print(started.read(8).hex(" "))
print(started.mode, started.offset, started.held)
```

```
00 00 00 00 00 00 00 15
00 f2 00 1d 00 e2 00 19
2 12 16
```

此例把 256 個位元組值按順序作為壓縮數據流交給晶片，並讀取 16 位元組的 4bpp 輸出，即模式 2。解碼這些位元組消耗了數據流中的 12 個位元組。晶片會預先解碼到一個 64 位元組的緩衝區，其中仍有 16 個已解碼位元組在等待讀取。

## 安裝

| 需求               | 版本                             |
| :----------------- | :------------------------------- |
| Python             | 3.12 或更新                      |
| git                | 任何版本                         |
| C++17 編譯器 `g++` | 僅在為差分檢查建置參考實現時需要 |

```bash
git clone https://github.com/gufranco/snes-spc7110-python.git
cd snes-spc7110-python
python3 spc7110/doctor.py
```

此套件只匯入標準程式庫中的模組。診斷腳本會檢查機器和工作副本，並以一行結果作結。它以檔案形式執行，因此即使套件本身無法匯入，它仍能報告。尚未建置參考實現的工作副本仍會通過，診斷腳本會說明差分檢查將被略過。提交任何錯誤報告時，請貼上其完整輸出。

```
  10 checks, nothing to report
```

所有檢查均通過時，它以 0 退出；任何一項未通過時，則以 1 退出。

版本發佈遵循 [Semantic Versioning](https://semver.org/)，由 semantic-release 根據提交歷史產生。每個版本都會加上標籤，並列於[版本發佈頁面](https://github.com/gufranco/snes-spc7110-python/releases)。

## 介面

`spc7110.Chip(model, rom=None, ram=None, seed=7110)` 用於建立晶片。`model` 為必填，沒有預設值。名稱比對時不區分大小寫、連字號、底線或空格，晶片會在 `model` 上保留其標準名稱。`rom` 是整個卡帶映像：首 1 MiB 是程式 ROM，其餘是數據 ROM。省略時，晶片會以 `seed` 打亂產生一個自己的 2 MiB 映像。`ram` 是存檔 RAM，類型為 `bytearray`，按傳入的物件原樣保留；省略時晶片不回應 `$6000-$7FFF`。所有暫存器上電時都按 `seed` 打亂，在 `reset()` 之前沒有任何暫存器具有確定的值。

| 型號      | 別名                       | 模式                   |
| :-------- | :------------------------- | :--------------------- |
| `spc7110` | `spc-7110`, `epsonspc7110` | `1bpp`, `2bpp`, `4bpp` |

### 呼叫

| 呼叫                                          | 作用                                                                                                                                                                         |
| :-------------------------------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `decompress(source, mode, offset=0, index=0)` | 以 `mode` 開始解壓 `source`，並傳回一個 `Decompressor`。`mode` 可以是名稱、別名或模式編號。`offset` 是 `source` 中開始的位元組。`index` 是首次讀取前要捨棄的已解碼位元組數目 |
| `reset()`                                     | 設定 ares 上電時設定的暫存器值，並捨棄任何正在等待的操作。傳回晶片本身                                                                                                       |
| `read(address)`                               | 讀取 24 位元 CPU 位址。傳回 `int`；對於 `$4800-$483F` 內晶片不驅動的暫存器，傳回 `None`                                                                                      |
| `write(address, value)`                       | 把 `value` 的低 8 位元寫入 24 位元 CPU 位址。寫入 ROM 不會改變任何內容                                                                                                       |
| `tick(clocks=1)`                              | 讓晶片前進 `clocks` 個主時鐘，每秒 21,477,272 個。解壓啟動、乘法及除法會在之後的某個時鐘完成。傳回晶片本身                                                                   |

| 屬性      | 意思                                                |
| :-------- | :-------------------------------------------------- |
| `rom`     | 傳入的或自行建立的卡帶映像                          |
| `program` | 程式 ROM，即 `rom` 的首 1 MiB，類型為 `bytes`       |
| `data`    | 數據 ROM，即首 1 MiB 之後的全部內容，類型為 `bytes` |
| `ram`     | 傳入的存檔 RAM，或 `None`                           |
| `model`   | 標準的型號名稱                                      |

`Decompressor` 是 `decompress` 傳回的物件。

| 呼叫或屬性                   | 含義                                                                     |
| :--------------------------- | :----------------------------------------------------------------------- |
| `read(count)`                | 以 `bytes` 傳回接下來 `count` 個已解碼位元組                             |
| `take_byte()`                | 以 `int` 傳回下一個已解碼位元組                                          |
| `row()`                      | 解碼一行八個像素，傳回其 1、2 或 4 個位元組，不經緩衝區                  |
| `start(mode, offset, index)` | 以模式編號 `mode` 重新開始解壓同一來源，並清除所有上下文。傳回解壓器本身 |
| `mode`                       | 模式編號，開始之前為 `None`                                              |
| `offset`                     | 解碼器將讀取的下一個來源位元組的索引                                     |
| `held`                       | 在 64 位元組緩衝區中等待讀取的已解碼位元組數目                           |
| `contexts`                   | 32 個機率上下文，每個都是 `Context`                                      |
| `source`                     | 壓縮數據流，已複製為 `bytes`；基於 `fetch` 建立時為 `b""`                |
| `fetch`                      | 讀取每個來源位元組時所呼叫的函數，參數為偏移量；沒有時為 `None`          |

解碼器的輸入會循環。讀取超出 `source` 結尾時，會從第 0 個位元組繼續，因為參考實現也是這樣做的。

```python
import spc7110

part = spc7110.Chip("spc7110")
stream = bytes(range(256))

whole = part.decompress(stream, 1).read(16)
later = part.decompress(stream, 1, offset=0, index=8).read(8)
print(whole[8:] == later)

moved = part.decompress(stream, 1, offset=200).read(4)
wrapped = part.decompress(stream[200:] + stream[:200], 1).read(4)
print(moved == wrapped)

for source, mode in ((stream, "16bpp"), (b"", "2bpp")):
    try:
        part.decompress(source, mode)
    except (spc7110.UnknownMode, spc7110.Empty) as error:
        print(type(error).__name__, error)
```

```
True
True
UnknownMode 16bpp is not a mode this chip has; it has 1bpp, 2bpp, 4bpp
Empty a decompressor needs something to decompress
```

以 `index` 捨棄 8 個位元組，所得的位元組與讀取 16 個再丟棄頭 8 個相同。從 `offset=200` 開始，所得的輸出與把數據流旋轉至第 200 個位元組排在最前時相同。

### 錯誤

| 錯誤                        | 引發時機                                                                |
| :-------------------------- | :---------------------------------------------------------------------- |
| `spc7110.UnknownModelError` | `Chip` 沒有獲得型號，或獲得的名稱不對應任何晶片。訊息會列出可接受的名稱 |
| `spc7110.UnknownMode`       | 模式名稱、別名或編號不屬於這三種之一。訊息會列出三個名稱                |
| `spc7110.Empty`             | 來源為空，卡帶映像在首 1 MiB 之後沒有數據 ROM，或傳入的存檔 RAM 為空    |
| `spc7110.OutOfRange`        | `read` 或 `write` 收到晶片不解碼的位址，或超出 24 位元的位址            |

這四種錯誤只在一處定義，即 [`spc7110/errors.py`](spc7110/errors.py)。

```python
import spc7110

for name, model in spc7110.MODELS.items():
    print(name, model.aliases, model.modes)

print(spc7110.Chip("SPC-7110").model, spc7110.Chip("epsonspc7110").model)
part = spc7110.Chip("spc7110")
print(part.reset() is part)

for named in (None, "spc7120"):
    try:
        spc7110.Chip(named)
    except spc7110.UnknownModelError as error:
        print(error)
```

```
spc7110 ('spc-7110', 'epsonspc7110') ('1bpp', '2bpp', '4bpp')
spc7110 spc7110
True
no model was named, and this package will not choose one for you. Name one of: spc7110
spc7120 is not a part this package covers; it has spc7110
```

### 模組內容

| 名稱                            | 內容                                                                                                                                                            |
| :------------------------------ | :-------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `spc7110.MODELS`                | 唯一的 `Model` 記錄，以標準名稱為鍵。`Model` 帶有 `name`、`aliases`、`modes`、`summary` 和 `build()`                                                            |
| `spc7110.MODES`                 | 三個 `Mode` 記錄，以名稱為鍵                                                                                                                                    |
| `spc7110.Mode`                  | 模式記錄：`number`、`name`、以每像素位元數表示的 `depth`、`aliases`、`summary`，以及用於開始一個 `Decompressor` 的 `build(source, offset=0, index=0)`           |
| `spc7110.mode_named(mode)`      | 給定 `int` 編號，或給定字串形式的名稱或別名時，傳回對應的 `Mode`。以字串寫成的編號，例如 `"2"`，會引發 `UnknownMode`                                            |
| `spc7110.Decompressor(source)`  | 解碼器本身，直接由數據流建立。在 `start` 指定模式之前，它不會產生任何輸出。`Decompressor(fetch=f)` 改為透過 `f(offset)` 讀取，晶片讀取數據 ROM 用的正是這種方式 |
| `spc7110.PROGRAM_BYTES`         | 1,048,576，卡帶映像開頭的程式 ROM 的大小                                                                                                                        |
| `spc7110.data_rom(image)`       | 卡帶映像的數據 ROM，即 `PROGRAM_BYTES` 之後的全部內容；之後沒有內容時為 `b""`                                                                                   |
| `spc7110.directory(drom, base)` | 位於 `base` 的數據流目錄：每次讀取四個位元組，直至遇到晶片沒有的模式、超出末端的位址或比上一個更小的位址為止，傳回 `(mode, address)` 項目清單以及停止處的偏移量 |
| `spc7110.chip`                  | 決定時序的常數：`MASTER_CLOCK_HZ`、`DECOMPRESSION_CLOCKS`、`MULTIPLY_CLOCKS`、`DIVIDE_CLOCKS` 及 `UNSET_SEED`                                                   |
| `spc7110.Context`               | 一個機率上下文：`index` 是它在演化表中的行，`invert` 是它目前視為較可能出現的符號                                                                               |
| `spc7110.CONTEXTS`              | 32，即上下文的數目                                                                                                                                              |
| `spc7110.tables`                | `EVOLUTION` 是 53 行機率、各符號之後的下一行及反轉旗標，`MODE2_CONTEXT` 是模式 2 的 32 個上下文轉移                                                             |
| `spc7110.__version__`           | 已安裝的版本                                                                                                                                                    |

```python
import spc7110

for mode in spc7110.MODES.values():
    print(mode.number, mode.name, mode.depth, mode.aliases)

for named in (2, "2-Colour", "MODE1"):
    print(named, spc7110.mode_named(named).name)

started = spc7110.Chip("spc7110").decompress(bytes(range(256)), "1bpp")
started.read(64)
print(spc7110.CONTEXTS, len(started.contexts), started.contexts[0])
print(len(spc7110.tables.EVOLUTION), len(spc7110.tables.MODE2_CONTEXT))
```

```
0 1bpp 1 ('mode0', '1bit', '2-colour')
1 2bpp 2 ('mode1', '2bit', '4-colour')
2 4bpp 4 ('mode2', '4bit', '16-colour')
2 4bpp
2-Colour 1bpp
MODE1 2bpp
32 32 <Context row 48 invert 0>
53 32
```

輸出 64 位元組的 1bpp 數據後，上下文 0 已由演化表的第 0 行移到第 48 行。

## 三種模式

三種模式之下都是同一個算術解碼器。模式決定一個符號帶有多少位元，以及之後如何處理它。

| 模式 | 名稱   | 產生         | 不同之處                                                               |
| :--- | :----- | :----------- | :--------------------------------------------------------------------- |
| 0    | `1bpp` | 每像素一位元 | 上下文來自最近的幾次判定，因為只有兩種顏色                             |
| 1    | `2bpp` | 每像素兩位元 | 四種顏色的最近使用列表，因此最近用過的顏色所需位元較少                 |
| 2    | `4bpp` | 每像素四位元 | 相同的列表，但涵蓋十六種顏色，並且整個 16 位元組的圖塊會先緩衝，再交回 |

解碼器中有兩處看似錯誤，其實不是。

**上下文可以調換它預期的符號。** 每個上下文帶有一個 `invert` 旗標，指明它視為較可能出現的符號；演化表中旗標已設定的 5 行，會在出現較不可能的符號時切換這個旗標。編解碼器正是以此追隨一條開頭是一種走向、之後轉為另一種走向的數據流。

**顏色列表是旋轉的，不是排序的。** 剛解碼的顏色移到最前，然後三個參考像素依次移到最前。編解碼器產生的數字是該列表的索引，因此同一個數字在相鄰像素之間代表不同的顏色。把列表排序或按數值順序保存的模型，能正確解碼最初幾個像素，之後便會漂移。

## 透過暫存器驅動它

遊戲從不直接把數據流交給晶片。它把目錄基址寫入 `$4801-$4803`，把索引寫入 `$4804`，以 `$4806` 啟動，等待 `$480C` 的第 7 位元，然後讀取 `$4800`。晶片透過自己的數據 ROM 映射讀取目錄項目和數據流，因此數據流永遠不會越過任何東西的末端而耗盡。

```python
import random

import spc7110

data = bytearray(random.Random(1).randbytes(0x10000))
data[8:12] = bytes((1, 0x00, 0x20, 0x00))
chip = spc7110.Chip("spc7110", rom=bytes(spc7110.PROGRAM_BYTES) + data).reset()

for register, value in ((0x4801, 0x08), (0x4802, 0x00), (0x4803, 0x00), (0x4804, 0x00)):
    chip.write(register, value)
chip.write(0x4806, 0x00)

print(hex(chip.tick(20).read(0x480C)), hex(chip.tick(1).read(0x480C)))
print(bytes(chip.read(0x4800) for _ in range(16)).hex(" "))
print(chip.read(0xD00000) == data[0], chip.read(0x581234))
```

```
0x0 0x80
46 a0 43 65 12 74 46 a1 97 b9 73 99 33 92 1b 32
True 0
```

`$000008` 的目錄項目指向 `$002000` 的模式 1。啟動在第 21 個主時鐘就緒：一個時鐘用於察覺請求，另外 20 個是 ares 所計的。重設後 `$4831` 為 0，所以 bank `$D0` 讀取數據 ROM 的第一個兆位元組；bank `$58` 以 `$4808` 的身份回應，讀出 0。

| 暫存器        | 單元       | 作用                                                                                                                            |
| :------------ | :--------- | :------------------------------------------------------------------------------------------------------------------------------ |
| `$4800-$480C` | 解壓       | 目錄基址、索引、跳過、步長、長度計數器、控制及狀態；`$4800` 以圖塊為單位交出已解碼的位元組                                      |
| `$4810-$481A` | 數據埠     | 在偏移量加上可選調整值的位置讀取數據 ROM，每次前進 1 或一個步長，可帶符號亦可不帶符號                                           |
| `$4820-$482F` | 運算       | 16 乘 16 的乘法及 32 除以 16 的除法，可帶符號亦可不帶符號；分別需要 30 及 40 個主時鐘，結果寫入之前 `$482F` 的第 7 位元表示忙碌 |
| `$4830-$4834` | 記憶體控制 | `$4830` 第 7 位元的存檔 RAM 啟用、bank `$D0`、`$E0` 及 `$F0` 所顯示的數據 ROM 兆位元組、數據 ROM 的大小以及第二個程式 bank      |

```python
import spc7110

chip = spc7110.Chip("spc7110").reset()
for register, value in ((0x4820, 0x34), (0x4821, 0x12), (0x4824, 0x78), (0x4825, 0x56)):
    chip.write(register, value)

print(hex(chip.read(0x482F)), hex(chip.tick(31).read(0x482F)))
print(bytes(chip.read(0x4828 + at) for at in range(4))[::-1].hex())

for address in (0x7E0000, 0x004840):
    try:
        chip.read(address)
    except spc7110.OutOfRange as error:
        print(error)
```

```
0x81 0x1
06260060
0x7e0000 is not an address the SPC7110 answers
0x004840 is not an address the SPC7110 answers
```

乘法在完成時才讀取運算元，所以在這 30 個時鐘內寫入 `$4820` 會改變乘積。`$4840-$4842` 是晶片旁邊的實時時鐘，由 [snes-rtc-python](https://github.com/gufranco/snes-rtc-python) 建模，因此這裏會拒絕這些位址。ares 和 snes9x 對某個暫存器意見不一時，晶片依從 ares，[`conformance/divergences.json`](conformance/divergences.json) 記錄了兩者。

## 它是否正確

目前不知道有這款晶片的任何廠商文件，這台機器上也沒有從真實 SPC7110 取得的任何錄製數據。廠商文件和硬件錄製數據這兩級證據在 [`conformance/hardware.json`](conformance/hardware.json) 中均標明為空。每個輸出值都依賴於與 snes9x 解壓器的一致。

```bash
python3 -m conformance.build
python3 -m conformance.differential
```

```
200 streams, 102,400 bytes compared, 0 disagreed
```

參考實現並未隨附在此。`conformance.build` 會按 [`conformance/pinned.json`](conformance/pinned.json) 中固定的提交取得 snes9x，在該固定記錄指定的兩條標記行之間，從其原始碼中截取解壓器，並以 `g++` 連同 [`conformance/ref/driver.cpp`](conformance/ref/driver.cpp) 編譯。若原始碼中的標記已移動，建置便會停止。建置成功時以 0 退出，編譯器失敗時以 1 退出，參數錯誤或取得失敗時以 2 退出。

| 工具                                        | 參數                                                                      | 退出碼                                                             |
| :------------------------------------------ | :------------------------------------------------------------------------ | :----------------------------------------------------------------- |
| `python3 -m conformance.build`              | `--sources DIR`、`--output PATH`、`--pinned PATH`、`--driver-source PATH` | 0 已建置，1 編譯失敗，2 用法錯誤或取得失敗                         |
| `python3 -m conformance.differential`       | `--seeds N`，預設 200，以及 `--driver PATH`                               | 0 全部一致，1 有任何分歧，2 沒有驅動程式或用法錯誤                 |
| `python3 -m conformance.cartridges`         | 一個卡帶目錄和一個輸出目錄                                                | 0 已記錄，2 找不到任何內容或用法錯誤                               |
| `python3 -m conformance.against_cartridges` | 一個卡帶目錄、一個輸出目錄，以及 `--driver PATH`                          | 0 全部一致，1 有任何分歧，2 找不到任何內容、沒有驅動程式或用法錯誤 |
| `python3 -m conformance.speed`              | 無                                                                        | 0 每秒解碼不少於 10,000 位元組，1 低於此值                         |

每個生成的案例包含來自帶種子產生器的 8,192 個位元組、由種子選定的模式、隨機的起始偏移，以及在奇數種子時最多 63 個被捨棄的位元組。兩邊都以相同的三項設定解碼 512 個位元組。執行器會列印最先出現分歧的 5 個案例。

### 經由暫存器，與 ares 比對

暫存器介面以提交 `9408cb43d4948fc3ea6e152a307a34348df3fe04` 的 ares 為準。我們把 ares 的解壓器原樣編譯進一個重現其圖塊邏輯的測試框架，並與 `spc7110.Chip` 一同經由暫存器驅動，涵蓋 619 條卡帶數據流及 231 個暫存器驅動的案例，當中包括隨機的跳過及步長：共 375,040 位元組，0 處分歧。[`conformance/hardware.json`](conformance/hardware.json) 在 `registerInterface` 下記錄了這次運行。測試框架沒有隨倉庫發佈，所以這是一次附日期的量度，而不是流水線會重複執行的檢查；而且 ares、bsnes 及 snes9x 都源自同一次逆向工程。

### 來自卡帶的數據流

隨機位元組會驅使解碼器進入編碼器永遠不會產生的狀態。真實數據流則驅使它進入編碼器會產生的狀態。兩者都會檢查。

`conformance.cartridges` 透過讀取遊戲自身程式碼寫入晶片的基址，找出每個卡帶中的數據流目錄，而不是靠搜尋某種模式。三個卡帶合共帶有 619 條數據流，三種模式都有涉及。[`conformance/cartridges.json`](conformance/cartridges.json) 記錄了數目、模式，以及每組數據流的熵，並與同一數據中隨機偏移處的熵作比較。`conformance.against_cartridges` 讓每一條這些數據流都經過兩個實現，[`conformance/streams.json`](conformance/streams.json) 記錄了結果：619 條數據流，316,928 位元組，0 處分歧。兩份記錄都帶有每個卡帶的四個摘要值，但不含任何卡帶的任何位元組。兩個實現在真實數據上一致，仍然只是兩個實現彼此一致，而且兩者都源自同一次逆向工程。

### 重現分歧

每個生成的案例都來自其種子，因此執行器指出的案例可以精確重建，並只由模型解碼。

```python
from conformance import differential

case = differential.cases(seeds=64)[63]
print(case)
print(bytes(differential.replay(case)[:8]).hex(" "))
```

```
<Case seed 63 mode 0 offset 3448 skip 35>
41 2f 61 31 d1 3d 7e 90
```

11 個未解決的問題，以及可以解決每個問題的測量，列於 [OPEN-QUESTIONS.md](OPEN-QUESTIONS.md)。當兩個來源出現分歧時，兩者都保留在 [`conformance/divergences.json`](conformance/divergences.json) 中，並附上可以判定的方法。

## 參與開發

| 需要                                 | 位置                                                                    |
| :----------------------------------- | :---------------------------------------------------------------------- |
| 每項關卡檢查及其執行順序             | [CONTRIBUTING.md](CONTRIBUTING.md)                                      |
| 寫給程式編寫代理的同一份資料         | [AGENTS.md](AGENTS.md)                                                  |
| 本儲存庫與同系列其他儲存庫共用的標準 | [FAMILY.md](FAMILY.md)                                                  |
| 錯誤報告                             | [GitHub Issues](https://github.com/gufranco/snes-spc7110-python/issues) |
| 安全報告                             | [SECURITY.md](SECURITY.md)                                              |

```bash
uvx ruff@0.16.3 format --check .
uvx ruff@0.16.3 check .
uvx --python 3.12 mypy==1.14.1
pnpm install --frozen-lockfile && pnpm run format:check
python3 -m coverage erase
for file in $(find spc7110 conformance -name '*.test.py' | sort); do
  python3 -m coverage run -a "$file"
done
python3 -m coverage report
python3 -m conformance.speed
```

每個模組旁邊都有一個以其命名的測試檔案，每個測試檔案都能獨立執行。覆蓋率是硬性關卡檢查，要求 100% 語句與分支覆蓋率。吞吐量下限在覆蓋率步驟之外執行，因此它量度的是解碼器，而不是追蹤器。

這些表格隨附於 [`spc7110/tables.py`](spc7110/tables.py)。它們是編解碼器參數：一個符號出現的可能性，以及接下來是哪一行。晶片透過自身暫存器所設定的數據 ROM 映射讀取數據流。它旁邊的實時時鐘是獨立的套件。

## 參考資料

本儲存庫不含任何文件，也不含任何卡帶數據。

- snes9x，提交 `2971061cf07fdc6fc7d18883edf4e648eb16a6d2` 中的 `spc7110dec.cpp` 和 `spc7110dec.h`，https://github.com/snes9xgit/snes9x ，用於所有輸出值。它在建置時取得並編譯，從不在此重新分發。
- ares，提交 `9408cb43d4948fc3ea6e152a307a34348df3fe04` 中的 `ares/sfc/coprocessor/spc7110`，https://github.com/ares-emulator/ares ，用於暫存器介面、其時序及 bank 映射。只採用事實，不取任何程式碼。
- snes9x，提交 `1bcc369e89f08243e0a462882fb1f3e42e51de3a` 中的 `spc7110emu.cpp` 和 `spc7110.cpp`，作為暫存器介面的第二個證據來源閱讀。

## 引用本專案

[CITATION.cff](CITATION.cff) 會在每次發佈版本時，由標記套件版本的腳本更新。

## 授權

MIT。見 [LICENSE](LICENSE)。參考實現是另一份作品，採用其自身的授權條款。
