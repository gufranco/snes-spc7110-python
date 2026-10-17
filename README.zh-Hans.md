# SPC7110 解压器

用 Python 实现的 SPC7110 解压器，涵盖它的全部三种输出模式，并逐字节与 snes9x 参考实现保持一致。

[English](README.md) &nbsp;|&nbsp; [日本語](README.ja.md) &nbsp;|&nbsp; 简体中文 &nbsp;|&nbsp; [繁體中文（香港）](README.zh-HK.md)

[![CI](https://github.com/gufranco/snes-spc7110-python/actions/workflows/ci.yml/badge.svg)](https://github.com/gufranco/snes-spc7110-python/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/gufranco/snes-spc7110-python)](https://github.com/gufranco/snes-spc7110-python/releases)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

**3** 种模式，**200** 条生成的数据流共 **102,400** 字节、**619** 条卡带数据流共 **316,928** 字节与参考实现比对，**0** 处不一致，**598** 个测试，**100%** 语句和分支覆盖率，无依赖

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

该示例把按顺序排列的 256 个字节值作为压缩数据流交给芯片，并读取 16 字节的 4bpp 输出，即模式 2。解码这些字节消耗了数据流的 12 个字节。芯片会提前解码到一个 64 字节的缓冲区中，其中仍有 16 个已解码字节在等待读取。

## 安装

| 要求 | 版本 |
|:--|:--|
| Python | 3.12 或更高 |
| git | 任意 |
| C++17 编译器 `g++` | 仅在为差分检查构建参考实现时需要 |

```bash
git clone https://github.com/gufranco/snes-spc7110-python.git
cd snes-spc7110-python
python3 spc7110/doctor.py
```

本包不导入标准库以外的任何内容。诊断脚本会检查本机和检出的代码，最后输出一行结果。它以文件方式运行，因此即使包本身无法导入，它仍能报告。尚未构建参考实现的检出仍会通过，诊断脚本会提示差分检查将被跳过。提交任何缺陷报告时，请粘贴它的完整输出。

```
  10 checks, nothing to report
```

所有检查都通过时它以 0 退出，任何一项未通过时以 1 退出。

版本发布遵循[语义化版本](https://semver.org/)，由 semantic-release 根据提交历史生成。每个版本都会打标签，并列在[发布页面](https://github.com/gufranco/snes-spc7110-python/releases)上。

## 接口

`spc7110.Chip(model)` 用于构建芯片。`model` 为必填项，没有默认值。名称匹配时不区分大小写，并忽略连字符、下划线和空格，芯片在 `model` 上保留其规范名称。

| 型号 | 别名 | 模式 |
|:--|:--|:--|
| `spc7110` | `spc-7110`、`epsonspc7110` | `1bpp`、`2bpp`、`4bpp` |

### 调用

| 调用 | 作用 |
|:--|:--|
| `decompress(source, mode, offset=0, index=0)` | 以 `mode` 开始对 `source` 进行解压，并返回一个 `Decompressor`。`mode` 可以是名称、别名或模式编号。`offset` 是 `source` 中开始的字节位置。`index` 是第一次读取前要丢弃的已解码字节数 |
| `reset()` | 返回芯片本身。解压结束后不会留下任何状态，因此它没有需要清除的内容 |

`Decompressor` 是 `decompress` 的返回值。

| 调用或属性 | 含义 |
|:--|:--|
| `read(count)` | 以 `bytes` 返回接下来的 `count` 个已解码字节 |
| `take_byte()` | 以 `int` 返回下一个已解码字节 |
| `start(mode, offset, index)` | 以模式编号 `mode` 重新开始解压同一数据源，并清除所有上下文。返回该解压器 |
| `mode` | 模式编号，开始之前为 `None` |
| `offset` | 解码器将要读取的下一个源字节的索引 |
| `held` | 在 64 字节缓冲区中等待的已解码字节 |
| `contexts` | 32 个概率上下文，每个都是一个 `Context` |
| `source` | 压缩数据流，已复制为 `bytes` |

解码器的输入会回绕。读取超过 `source` 末尾时会从第 0 个字节继续，因为参考实现也是如此。

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

用 `index` 丢弃 8 个字节，得到的字节与读取 16 个字节再去掉前 8 个相同。从 `offset=200` 开始，得到的输出与把数据流旋转到第 200 个字节位于开头时相同。

### 错误

| 错误 | 引发条件 |
|:--|:--|
| `spc7110.UnknownModelError` | 未给 `Chip` 指定型号，或给出的名称不对应任何芯片。消息会列出可接受的名称 |
| `spc7110.UnknownMode` | 模式名称、别名或编号不属于这三种之一。消息会列出这三个名称 |
| `spc7110.Empty` | 数据源为空 |

这三种错误都只在 [`spc7110/errors.py`](spc7110/errors.py) 中定义一次。

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

### 模块内容

| 名称 | 内容 |
|:--|:--|
| `spc7110.MODELS` | 唯一的 `Model` 记录，以规范名称为键。`Model` 包含 `name`、`aliases`、`modes`、`summary` 和 `build()` |
| `spc7110.MODES` | 三条 `Mode` 记录，以名称为键 |
| `spc7110.Mode` | 模式记录：`number`、`name`、以每像素位数表示的 `depth`、`aliases`、`summary`，以及启动一个 `Decompressor` 的 `build(source, offset=0, index=0)` |
| `spc7110.mode_named(mode)` | 以 `int` 给出编号时，或以字符串给出名称或别名时，返回对应的 `Mode`。以字符串写出的编号，例如 `"2"`，会引发 `UnknownMode` |
| `spc7110.Decompressor(source)` | 解码器本身，直接由数据流构建。在 `start` 指定模式之前它不产生任何输出 |
| `spc7110.Context` | 一个概率上下文：`index` 是它在演进表中的行，`invert` 表示它当前把哪个符号视为较可能的符号 |
| `spc7110.CONTEXTS` | 32，即上下文的数量 |
| `spc7110.tables` | `EVOLUTION` 是 53 行数据，每行包含概率、各符号对应的下一行和反转标志；`MODE2_CONTEXT` 是模式 2 的 32 个上下文转换 |
| `spc7110.__version__` | 已安装的版本 |

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

输出 64 字节的 1bpp 数据后，上下文 0 已从演进表的第 0 行移到第 48 行。

## 三种模式

三种模式底层共用一个算术解码器。模式决定一个符号携带多少位，以及之后如何处理它。

| 模式 | 名称 | 产生 | 不同之处 |
|:--|:--|:--|:--|
| 0 | `1bpp` | 每像素一位 | 上下文来自最近几次判定，因为只有两种颜色 |
| 1 | `2bpp` | 每像素两位 | 四种颜色的最近使用列表，最近用过的颜色所需的位数更少 |
| 2 | `4bpp` | 每像素四位 | 同样的列表，覆盖十六种颜色，并且会先缓冲完整的 16 字节图块再交回 |

解码器中有两处看起来像错误，但其实不是。

**上下文可以交换它所预期的符号。** 每个上下文带有一个 `invert` 标志，指明它视为较可能的符号；演进表中有 5 行设置了该标志，这些行在遇到不太可能的符号时会切换它。编码器正是靠这一点跟随一条开头是一种模式、后面变成另一种模式的数据流。

**颜色列表是旋转的，而不是排序的。** 刚解码出的颜色移到最前面，然后三个参考像素依次移到最前面。编码器产生的数字是该列表中的索引，因此同一个数字在相邻像素之间代表不同的颜色。对列表排序或按值顺序保存列表的模型，前几个像素能正确解码，之后就会逐渐偏离。

## 它是否正确

目前没有已知的该芯片厂商文档，本机上也没有从真实 SPC7110 采集的记录。厂商文档和硬件记录这两级依据在 [`conformance/hardware.json`](conformance/hardware.json) 中都标注为空。所有输出值都以与 snes9x 解压器的一致性为依据。

```bash
python3 -m conformance.build
python3 -m conformance.differential
```

```
200 streams, 102,400 bytes compared, 0 disagreed
```

参考实现没有内置在仓库中。`conformance.build` 会获取 [`conformance/pinned.json`](conformance/pinned.json) 中固定提交的 snes9x，在固定记录指定的两条标记行之间从其源代码中截取解压器，并用 `g++` 与 [`conformance/ref/driver.cpp`](conformance/ref/driver.cpp) 一起编译。如果源代码中的标记位置发生变化，构建会停止。构建成功时以 0 退出，编译器失败时以 1 退出，参数错误或获取失败时以 2 退出。

| 工具 | 参数 | 退出码 |
|:--|:--|:--|
| `python3 -m conformance.build` | `--sources DIR`、`--output PATH`、`--pinned PATH`、`--driver-source PATH` | 0 构建成功，1 编译失败，2 用法错误或获取失败 |
| `python3 -m conformance.differential` | `--seeds N`，默认 200，以及 `--driver PATH` | 0 全部一致，1 存在不一致，2 无驱动程序或用法错误 |
| `python3 -m conformance.cartridges` | 一个卡带目录和一个输出目录 | 0 已记录，2 未找到任何内容或用法错误 |
| `python3 -m conformance.against_cartridges` | 一个卡带目录、一个输出目录和 `--driver PATH` | 0 全部一致，1 存在不一致，2 未找到任何内容、无驱动程序或用法错误 |
| `python3 -m conformance.speed` | 无 | 0 达到或超过每秒 10,000 个解码字节，1 低于该值 |

每个生成的用例包括：由带种子的生成器产生的 8,192 字节、由种子选定的模式、随机的起始偏移，以及在奇数种子上最多 63 个丢弃字节。两边都按相同的三项设置解码 512 字节。运行器会打印前 5 个不一致的用例。

### 来自卡带的数据流

随机字节会把解码器带入编码器永远不会产生的状态。真实数据流则把它带入编码器会产生的状态。两者都会检查。

`conformance.cartridges` 通过读取游戏自身代码写入芯片的基地址来找到每个卡带中的数据流目录，而不是通过搜索特征模式。三个卡带共包含 619 条数据流，覆盖全部三种模式。[`conformance/cartridges.json`](conformance/cartridges.json) 记录了数量、模式，以及每组数据流的熵与同一数据中随机偏移处的熵的对比。`conformance.against_cartridges` 让其中每一条数据流都经过两个实现，[`conformance/streams.json`](conformance/streams.json) 记录了结果：619 条数据流，316,928 字节，0 处不一致。两份记录都包含每个卡带的四个摘要，但不包含其中任何一个字节。两个实现在真实数据上一致，仍然只是两个实现彼此一致，而且两者都源自同一次逆向工程。

### 复现不一致

每个生成的用例都来自其种子，因此运行器指出的用例可以被精确重建，并仅由模型解码。

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

7 个未解决的问题，以及能够解决每个问题的测量方法，都在 [OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) 中。两个来源出现分歧时，两者都保留在 [`conformance/divergences.json`](conformance/divergences.json) 中，并附有能够判定分歧的依据。

## 参与开发

| 需要 | 位置 |
|:--|:--|
| 所有门禁检查及其运行顺序 | [CONTRIBUTING.md](CONTRIBUTING.md) |
| 面向编码代理的相同内容 | [AGENTS.md](AGENTS.md) |
| 本仓库与同系列其他仓库共享的标准 | [FAMILY.md](FAMILY.md) |
| 缺陷报告 | [GitHub Issues](https://github.com/gufranco/snes-spc7110-python/issues) |
| 安全报告 | [SECURITY.md](SECURITY.md) |

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

每个模块旁边都有一个以其命名的测试文件，每个测试文件都可以单独运行。覆盖率是硬性门禁检查，要求语句和分支覆盖率均为 100%。吞吐量下限检查在覆盖率步骤之外运行，因此它测量的是解码器，而不是跟踪器。

这些表位于 [`spc7110/tables.py`](spc7110/tables.py) 中。它们是编码器参数：一个符号出现的可能性有多大，以及下一行是哪一行。解压器以字节形式接收数据流。数据流位于卡带中的什么位置属于映射问题，该芯片的映射器和实时时钟是单独的包。

## 参考资料

本仓库不包含任何文档，也不包含任何卡带数据。

- snes9x，提交 `2971061cf07fdc6fc7d18883edf4e648eb16a6d2` 中的 `spc7110dec.cpp` 和 `spc7110dec.h`，https://github.com/snes9xgit/snes9x ，用于所有输出值。它在构建时获取并编译，从不在此重新分发。

## 引用本项目

[CITATION.cff](CITATION.cff) 会在每次发布时由写入包版本的脚本更新。

## 许可证

MIT。见 [LICENSE](LICENSE)。参考实现是一个独立的作品，适用其自身的许可证。
