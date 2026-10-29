# SPC7110デコンプレッサ

SPC7110をPythonで実装したものです。3つの出力モードすべてを備えたデコンプレッサはsnes9xとバイト単位で一致させ、コンソールがそこへ到達するためのレジスタはaresに合わせています。

[English](README.md) | 日本語 | [简体中文](README.zh-Hans.md) | [繁體中文（香港）](README.zh-HK.md)

[![ci](https://img.shields.io/github/actions/workflow/status/gufranco/snes-spc7110-python/ci.yml?branch=main&style=flat-square&label=ci)](https://github.com/gufranco/snes-spc7110-python/actions/workflows/ci.yml)
[![release](https://img.shields.io/github/v/release/gufranco/snes-spc7110-python?style=flat-square&label=release)](https://github.com/gufranco/snes-spc7110-python/releases/latest)
[![coverage](https://img.shields.io/badge/coverage-100%25-brightgreen?style=flat-square)](https://github.com/gufranco/snes-spc7110-python/actions/workflows/ci.yml)
[![openssf scorecard](https://img.shields.io/ossf-scorecard/github.com/gufranco/snes-spc7110-python?style=flat-square&label=openssf%20scorecard)](https://scorecard.dev/viewer/?uri=github.com/gufranco/snes-spc7110-python)
[![license](https://img.shields.io/github/license/gufranco/snes-spc7110-python?style=flat-square&label=license)](LICENSE)

**3**モード、**102,400**バイトにわたる生成ストリーム**200**本と**316,928**バイトにわたるカートリッジのストリーム**619**本をリファレンスと比較、レジスタ経由で読んだカートリッジのストリーム**619**本とレジスタ駆動のケース**231**件をaresと比較、不一致**0**件、テスト**833**件、ステートメントとブランチのカバレッジ**100%**、依存パッケージなし

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

この例では、256個のバイト値を順番に並べたものを圧縮ストリームとしてチップに渡し、モード2である4bppの出力を16バイト読み出しています。これをデコードするのにストリームの12バイトを消費しました。チップは64バイトのバッファへ先行してデコードしており、そこにはデコード済みの16バイトがまだ残っています。

## インストール

| 要件                   | バージョン                                       |
| :--------------------- | :----------------------------------------------- |
| Python                 | 3.12以降                                         |
| git                    | 任意                                             |
| C++17コンパイラ、`g++` | 差分チェック用のリファレンスをビルドする場合のみ |

```bash
git clone https://github.com/gufranco/snes-spc7110-python.git
cd snes-spc7110-python
python3 spc7110/doctor.py
```

このパッケージは標準ライブラリ以外を何もインポートしません。ドクターはマシンとチェックアウトを確認し、1行で結果を出して終了します。ファイルとして実行されるため、パッケージ自体がインポートできない場合でも報告を出します。リファレンスがビルドされていないチェックアウトでも合格となり、その場合ドクターは差分チェックがスキップされることを伝えます。バグ報告には出力全体を貼り付けてください。

```
  10 checks, nothing to report
```

すべてのチェックに合格すると0で、1つでも合格しなければ1で終了します。

リリースは[Semantic Versioning](https://semver.org/)に従い、semantic-releaseによってコミット履歴から作成されます。各リリースにはタグが付けられ、[リリースページ](https://github.com/gufranco/snes-spc7110-python/releases)に掲載されます。

## インターフェース

`spc7110.Chip(model, rom=None, ram=None, seed=7110)`でチップを構築します。`model`は必須で、デフォルト値はありません。名前は大文字と小文字、ハイフン、アンダースコア、スペースの違いを無視して照合され、チップは正規名を`model`に保持します。`rom`はカートリッジイメージ全体で、先頭の1 MiBがプログラムROM、残りがデータROMです。省略すると、チップは`seed`からスクランブルした2 MiBのイメージを自分で構築します。`ram`はセーブRAMを表す`bytearray`で、渡されたものをそのまま保持します。省略すると`$6000-$7FFF`には何も応答しません。すべてのレジスタは`seed`からスクランブルされた状態で立ち上がり、`reset()`まではどれも定義された値を持ちません。

| モデル    | 別名                       | モード                 |
| :-------- | :------------------------- | :--------------------- |
| `spc7110` | `spc-7110`、`epsonspc7110` | `1bpp`、`2bpp`、`4bpp` |

### 呼び出し

| 呼び出し                                      | 効果                                                                                                                                                                                                                  |
| :-------------------------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `decompress(source, mode, offset=0, index=0)` | `source`を`mode`で展開し始め、`Decompressor`を返します。`mode`は名前、別名、またはモード番号です。`offset`は`source`のどのバイトから始めるかを示します。`index`は最初の読み出しの前に捨てるデコード済みバイトの数です |
| `reset()`                                     | aresが電源投入時に設定するレジスタ値を設定し、待機中の処理を破棄します。チップ自身を返します                                                                                                                          |
| `read(address)`                               | 24ビットのCPUアドレスを読みます。`int`を返し、`$4800-$483F`の中でチップが駆動しないレジスタでは`None`を返します                                                                                                       |
| `write(address, value)`                       | `value`の下位8ビットを24ビットのCPUアドレスへ書き込みます。ROMへの書き込みは何も変えません                                                                                                                            |
| `tick(clocks=1)`                              | チップを`clocks`マスタークロック分進めます。1秒あたり21,477,272です。展開の開始、乗算、除算は後のクロックで完了します。チップ自身を返します                                                                           |

| 属性      | 意味                                                                |
| :-------- | :------------------------------------------------------------------ |
| `rom`     | 渡された、または構築されたカートリッジイメージです                  |
| `program` | プログラムROM、つまり`rom`の先頭1 MiBを`bytes`で表したものです      |
| `data`    | データROM、つまり先頭1 MiBより後ろのすべてを`bytes`で表したものです |
| `ram`     | 渡されたセーブRAM、または`None`です                                 |
| `model`   | 正規のモデル名です                                                  |

`Decompressor`は`decompress`が返すオブジェクトです。

| 呼び出しまたは属性           | 意味                                                                                               |
| :--------------------------- | :------------------------------------------------------------------------------------------------- |
| `read(count)`                | 次の`count`個のデコード済みバイトを`bytes`として返します                                           |
| `take_byte()`                | 次のデコード済みバイトを`int`として返します                                                        |
| `row()`                      | 8ピクセル分の1行をデコードし、その1、2、4バイトを返します。バッファは経由しません                  |
| `start(mode, offset, index)` | 同じソースをモード番号`mode`で再開し、すべてのコンテキストをクリアします。デコンプレッサを返します |
| `mode`                       | モード番号です。開始前は`None`です                                                                 |
| `offset`                     | デコーダが次に取り込むソースバイトのインデックスです                                               |
| `held`                       | 64バイトのバッファに残っているデコード済みバイトです                                               |
| `contexts`                   | 32個の確率コンテキストで、それぞれが`Context`です                                                  |
| `source`                     | `bytes`にコピーされた圧縮ストリームです。`fetch`の上に構築した場合は`b""`です                      |
| `fetch`                      | 各ソースバイトを、オフセットを渡して読むための関数です。なければ`None`です                         |

デコーダは入力を循環させます。`source`の末尾を越えた読み出しはバイト0から続きます。リファレンスも同じ動作をするためです。

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

`index`で8バイトを捨てると、16バイトを読んで先頭の8バイトを落とした場合と同じバイトが得られます。`offset=200`から始めると、バイト200が先頭に来るようにストリームを回転させた場合と同じ出力が得られます。

### エラー

| エラー                      | 発生する条件                                                                                                                         |
| :-------------------------- | :----------------------------------------------------------------------------------------------------------------------------------- |
| `spc7110.UnknownModelError` | `Chip`にモデルが渡されなかった場合、またはどのチップにも該当しない名前が渡された場合です。メッセージには受け付ける名前が列挙されます |
| `spc7110.UnknownMode`       | モード名、別名、または番号が3つのいずれでもない場合です。メッセージには3つの名前が列挙されます                                       |
| `spc7110.Empty`             | ソースが空の場合、カートリッジイメージの先頭1 MiBの後ろにデータROMがない場合、または渡されたセーブRAMが空の場合です                  |
| `spc7110.OutOfRange`        | `read`または`write`に、チップがデコードしないアドレスか24ビットを超えるアドレスが渡された場合です                                    |

4つとも[`spc7110/errors.py`](spc7110/errors.py)で一度だけ定義されています。

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

### モジュールの内容

| 名前                            | 内容                                                                                                                                                                                                         |
| :------------------------------ | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `spc7110.MODELS`                | 唯一の`Model`レコードで、正規名をキーとします。`Model`は`name`、`aliases`、`modes`、`summary`、`build()`を持ちます                                                                                           |
| `spc7110.MODES`                 | 3つの`Mode`レコードで、名前をキーとします                                                                                                                                                                    |
| `spc7110.Mode`                  | モードのレコードです。`number`、`name`、1ピクセルあたりのビット数を表す`depth`、`aliases`、`summary`、そして`Decompressor`を開始する`build(source, offset=0, index=0)`を持ちます                             |
| `spc7110.mode_named(mode)`      | `int`で与えた番号、または文字列で与えた名前や別名に対応する`Mode`です。`"2"`のように文字列で書いた番号は`UnknownMode`を送出します                                                                            |
| `spc7110.Decompressor(source)`  | ストリームから直接構築するデコーダ本体です。`start`がモードを指定するまで何も出力しません。`Decompressor(fetch=f)`は代わりに`f(offset)`を通して読みます。チップがデータROMを読むのはこの方法です             |
| `spc7110.PROGRAM_BYTES`         | 1,048,576、カートリッジイメージの先頭にあるプログラムROMのサイズです                                                                                                                                         |
| `spc7110.data_rom(image)`       | カートリッジイメージのデータROM、つまり`PROGRAM_BYTES`より後ろのすべてです。後ろに何もなければ`b""`です                                                                                                      |
| `spc7110.directory(drom, base)` | `base`にあるストリームディレクトリです。チップにないモード、末尾を越えるアドレス、または直前より小さいアドレスに当たるまで4バイトずつ読んだ`(mode, address)`エントリのリストと、止まったオフセットを返します |
| `spc7110.chip`                  | タイミングを決める定数、`MASTER_CLOCK_HZ`、`DECOMPRESSION_CLOCKS`、`MULTIPLY_CLOCKS`、`DIVIDE_CLOCKS`、`UNSET_SEED`です                                                                                      |
| `spc7110.Context`               | 1つの確率コンテキストです。遷移表での行を表す`index`と、現在どちらのシンボルを出やすい方とみなしているかを表す`invert`を持ちます                                                                             |
| `spc7110.CONTEXTS`              | コンテキストの数である32です                                                                                                                                                                                 |
| `spc7110.tables`                | 確率、各シンボルでの次の行、反転フラグからなる53行の`EVOLUTION`と、モード2の32個のコンテキスト遷移である`MODE2_CONTEXT`です                                                                                  |
| `spc7110.__version__`           | インストールされているバージョンです                                                                                                                                                                         |

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

1bppの出力を64バイト読んだ後、コンテキスト0は遷移表の行0から行48へ移動しています。

## 3つのモード

3つのモードの下には1つの算術デコーダがあります。モードは、1つのシンボルが何ビットを運ぶか、そしてその後シンボルがどう扱われるかを決めます。

| モード | 名前   | 出力                   | 違い                                                                   |
| :----- | :----- | :--------------------- | :--------------------------------------------------------------------- |
| 0      | `1bpp` | 1ピクセルあたり1ビット | 色が2つしかないため、コンテキストは直近のいくつかの判定から決まります  |
| 1      | `2bpp` | 1ピクセルあたり2ビット | 4色の使用順リストを持ち、最近使った色ほど少ないビットで済みます        |
| 2      | `4bpp` | 1ピクセルあたり4ビット | 同じリストを16色で持ち、16バイトのタイル全体をバッファしてから返します |

デコーダには誤りに見えて誤りではない点が2つあります。

**コンテキストは予期するシンボルを入れ替えることがあります。** 各コンテキストは出やすいとみなすシンボルを示す`invert`フラグを持ち、フラグが立っている遷移表の5つの行では、出にくいシンボルが来るとこのフラグが反転します。これにより、コーダはある傾向で始まり別の傾向で続くストリームに追従します。

**色のリストはソートではなく回転されます。** 直前にデコードした色が先頭に移り、続いて3つの参照ピクセルが順に先頭へ移されます。コーダが出力する数値はこのリストへのインデックスなので、同じ数値でもピクセルごとに異なる色を意味します。リストをソートしたり値の順に保ったりするモデルは、最初の数ピクセルを正しくデコードした後にずれていきます。

## レジスタを通して動かす

ゲームはチップにストリームを直接渡すことはありません。ディレクトリのベースを`$4801-$4803`に、インデックスを`$4804`に書き込み、`$4806`で開始し、`$480C`のビット7を待ってから`$4800`を読みます。チップはディレクトリのエントリとストリームを自身のデータROMマッピングを通して読むため、ストリームが何かの末尾を越えて尽きることはありません。

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

`$000008`のディレクトリエントリは`$002000`にあるモード1を指しています。開始は21番目のマスタークロックで準備が整います。1クロックは要求に気づくため、残りの20はaresが課すものです。リセット後の`$4831`は0なので、バンク`$D0`はデータROMの最初の1メガバイトを読みます。バンク`$58`は`$4808`として応答し、これは0を読みます。

| レジスタ      | ユニット     | 役割                                                                                                                                        |
| :------------ | :----------- | :------------------------------------------------------------------------------------------------------------------------------------------ |
| `$4800-$480C` | 展開         | ディレクトリのベース、インデックス、シーク、ストライド、長さのカウンタ、制御、状態です。`$4800`はデコード済みのバイトをタイル単位で渡します |
| `$4810-$481A` | データポート | オフセットと任意の調整値の位置でデータROMを読み、1ずつまたはストライドずつ、符号付きまたは符号なしで進みます                                |
| `$4820-$482F` | 演算         | 16×16の乗算と32÷16の除算で、符号付きと符号なしがあります。30と40マスタークロックかかり、結果が入るまで`$482F`のビット7がビジーを示します    |
| `$4830-$4834` | メモリ制御   | `$4830`のビット7のセーブRAM有効化、バンク`$D0`、`$E0`、`$F0`が見せるデータROMのメガバイト、データROMのサイズ、2番目のプログラムバンクです   |

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

乗算は完了時にオペランドを読むため、30クロックの間に`$4820`へ書き込むと積が変わります。`$4840-$4842`はチップの隣にあるリアルタイムクロックで、[snes-rtc-python](https://github.com/gufranco/snes-rtc-python)がモデル化しているため、ここでは拒否されます。aresとsnes9xでレジスタの扱いが異なる箇所では、チップはaresに従い、[`conformance/divergences.json`](conformance/divergences.json)に両方を記録しています。

## 正しいのか

このチップについてのメーカー文書は知られておらず、実機のSPC7110から取った記録もこのマシンにはありません。メーカー文書と実機の記録という2つの証拠の段階がどちらも空であることが[`conformance/hardware.json`](conformance/hardware.json)に明記されています。すべての出力値は、snes9xのデコンプレッサとの一致を根拠としています。

```bash
python3 -m conformance.build
python3 -m conformance.differential
```

```
200 streams, 102,400 bytes compared, 0 disagreed
```

リファレンスは同梱していません。`conformance.build`は[`conformance/pinned.json`](conformance/pinned.json)で固定されたコミットのsnes9xを取得し、固定情報が指定する2つのマーカー行の間からデコンプレッサをソースから切り出し、[`conformance/ref/driver.cpp`](conformance/ref/driver.cpp)と合わせて`g++`でコンパイルします。マーカーの位置が変わったソースではビルドが停止します。ビルドできた場合は0、コンパイラが失敗した場合は1、引数が不正な場合や取得に失敗した場合は2で終了します。

| ツール                                      | 引数                                                                      | 終了コード                                                                   |
| :------------------------------------------ | :------------------------------------------------------------------------ | :--------------------------------------------------------------------------- |
| `python3 -m conformance.build`              | `--sources DIR`、`--output PATH`、`--pinned PATH`、`--driver-source PATH` | 0 ビルド成功、1 コンパイル失敗、2 使用法の誤りまたは取得失敗                 |
| `python3 -m conformance.differential`       | `--seeds N`（デフォルト200）、`--driver PATH`                             | 0 すべて一致、1 不一致あり、2 ドライバなしまたは使用法の誤り                 |
| `python3 -m conformance.cartridges`         | カートリッジのディレクトリと出力ディレクトリ                              | 0 記録済み、2 見つからないまたは使用法の誤り                                 |
| `python3 -m conformance.against_cartridges` | カートリッジのディレクトリ、出力ディレクトリ、`--driver PATH`             | 0 すべて一致、1 不一致あり、2 見つからない、ドライバなし、または使用法の誤り |
| `python3 -m conformance.speed`              | なし                                                                      | 0 毎秒10,000デコードバイト以上、1 それ未満                                   |

生成される各ケースは、シード付きジェネレータによる8,192バイト、シードで選ばれるモード、ランダムな開始オフセット、そして奇数シードでは最大63バイトの破棄バイトからなります。両者は同じ3つの設定から512バイトをデコードします。ランナーは不一致となった最初の5ケースを表示します。

### レジスタを通して、aresと比較

レジスタインターフェースはコミット`9408cb43d4948fc3ea6e152a307a34348df3fe04`のaresに合わせています。aresのデコンプレッサを変更せずに、そのタイル処理を再現するハーネスの中でコンパイルし、`spc7110.Chip`と並べてレジスタ経由で、カートリッジのストリーム619本とレジスタ駆動のケース231件を駆動しました。ランダムなシークとストライドを含み、375,040バイト、不一致0件です。[`conformance/hardware.json`](conformance/hardware.json)の`registerInterface`にこの実行を記録しています。ハーネスは同梱していないため、これはパイプラインが繰り返すチェックではなく日付付きの測定です。また、ares、bsnes、snes9xはすべて同じ1つのリバースエンジニアリングに由来しています。

### カートリッジのストリーム

ランダムなバイトは、エンコーダが決して生み出さない状態へデコーダを導きます。実際のストリームは、エンコーダが生み出す状態へ導きます。両方を確認しています。

`conformance.cartridges`は、パターンを検索するのではなく、ゲーム自身のコードがチップに書き込むベースアドレスを読むことで、各カートリッジのストリームディレクトリを見つけます。3本のカートリッジに合計619本のストリームがあり、3つのモードすべてに到達しています。[`conformance/cartridges.json`](conformance/cartridges.json)には、その本数、モード、そして各ストリーム群のエントロピーを同じデータ内のランダムなオフセットと比べた結果が記録されています。`conformance.against_cartridges`はそれらのストリームをすべて両方の実装に通し、[`conformance/streams.json`](conformance/streams.json)にその結果を記録します。619本のストリーム、316,928バイト、不一致0件です。どちらの記録も各カートリッジの4つのダイジェストを持ちますが、カートリッジのバイトは1つも含みません。実データで2つの実装が一致しても、それは2つの実装が一致したということに過ぎず、両者は同じ1つのリバースエンジニアリングに由来しています。

### 不一致の再現

生成される各ケースはそのシードから作られるため、ランナーが示したケースは正確に再構築でき、モデル単独でデコードできます。

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

11の未解決の問題と、それぞれを解決する測定は[OPEN-QUESTIONS.md](OPEN-QUESTIONS.md)にあります。2つの情報源の見解が分かれる箇所は、両方とも[`conformance/divergences.json`](conformance/divergences.json)に、決着をつける方法とともに残しています。

## 開発

| 必要なもの                                               | 場所                                                                    |
| :------------------------------------------------------- | :---------------------------------------------------------------------- |
| すべてのゲートと実行順序                                 | [CONTRIBUTING.md](CONTRIBUTING.md)                                      |
| コーディングエージェント向けの同じ内容                   | [AGENTS.md](AGENTS.md)                                                  |
| このリポジトリがファミリーの他のリポジトリと共有する基準 | [FAMILY.md](FAMILY.md)                                                  |
| バグ報告                                                 | [GitHub Issues](https://github.com/gufranco/snes-spc7110-python/issues) |
| セキュリティ報告                                         | [SECURITY.md](SECURITY.md)                                              |

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

各モジュールの隣には、そのモジュールにちなんだ名前のテストファイルがあり、それぞれ単独で実行できます。カバレッジはステートメントとブランチの100%を必須とするゲートです。スループットの下限チェックはカバレッジのステップの外で実行されるため、トレーサーではなくデコーダを測定します。

テーブルは[`spc7110/tables.py`](spc7110/tables.py)に含まれています。これらはコーダのパラメータで、シンボルがどれだけ出やすいか、次にどの行が続くかを表します。チップは自身のレジスタが設定するデータROMマッピングを通してストリームを読みます。隣にあるリアルタイムクロックは別のパッケージです。

## 参考文献

このリポジトリには文書もカートリッジのデータも含まれていません。

- snes9x、コミット`2971061cf07fdc6fc7d18883edf4e648eb16a6d2`の`spc7110dec.cpp`と`spc7110dec.h`、https://github.com/snes9xgit/snes9x 。すべての出力値の根拠です。ビルド時に取得してコンパイルし、ここで再配布することはありません。
- ares、コミット`9408cb43d4948fc3ea6e152a307a34348df3fe04`の`ares/sfc/coprocessor/spc7110`、https://github.com/ares-emulator/ares 。レジスタインターフェース、そのタイミング、バンクマッピングの根拠です。事実のみを用い、コードは取り込んでいません。
- snes9x、コミット`1bcc369e89f08243e0a462882fb1f3e42e51de3a`の`spc7110emu.cpp`と`spc7110.cpp`。レジスタインターフェースの2番目の証人として読みました。

## 引用

[CITATION.cff](CITATION.cff)は、パッケージのバージョンを書き込むスクリプトによってリリースごとに更新されます。

## ライセンス

MITです。[LICENSE](LICENSE)を参照してください。リファレンス実装は独自のライセンスの下にある別の著作物です。
