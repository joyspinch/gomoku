# 五子棋 · GOMOKU

> 点击落子，先连成五子者胜；启发式 AI 对弈，悬停显示落子预览。

用 [Zan](https://github.com/joyspinch/zan-lang) 语言写的独立游戏项目（仓库根自带 git 仓库）。完整设计与实现说明见 [`PROJECT.md`](PROJECT.md)。

## 玩法

- 点击落子，先连成五子者胜
- 启发式 AI 对弈，悬停显示落子预览
- R 重新开局，Esc 退出

## 构建

需要 [zan-lang](https://github.com/joyspinch/zan-lang) 仓库（`zanc` 编译器、公共包与 stdlib 都在里面）：

```powershell
git clone https://github.com/joyspinch/zan-lang.git
$env:ZAN_HOME = 'D:/path/to/zan-lang'   # 指到刚克隆的 zan-lang 仓库根

pwsh -File client/tools/build.ps1
```

产物：`build/gomoku/Gomoku.exe`（运行目录要带上它旁边的 `assets/` 与 `skins/`）。

## 运行

```powershell
cd build/gomoku
.\Gomoku.exe
```

## 测试

```powershell
pwsh -File client/tools/test.ps1
```

## 目录结构

```
gomoku/
client/
  src/      # 游戏源码（.zan 源码 + HTML 界面设计稿）
  assets/   # 位图 / 音频素材
  tests/    # 玩法断言用例
  tools/    # 构建与测试脚本
PROJECT.md
```

## 素材与授权

- **大背景图已改为本地程序化生成**：`client/assets/menu_bg.png`、`menu_bg2.png`、`play_bg.png` 由仓内 `client/tools/make_bgs.py` 生成（纯 numpy + PIL，无外部素材来源），重新生成命令 `python client/tools/make_bgs.py`。
- **木纹棋盘 / 黑白子 / 结算面板 / 标题由图像模型生成**：这批素材源自 zan-lang 早期五子棋模板，由图像模型（gpt-image-2）产出，生成管线为 zan-lang 的 `scripts/gen_assets.ps1` 与 `scripts/gen_game_art.ps1`（统一风格串见 `assets/game/style.md`，棋类品类限定词 `clean puzzle-piece iconography, flat readable shapes`），生成后做绿幕抠图与裁边缩放。逐项来源可追溯：
  - `board_wood.png` —— [zan-lang `1c586f33`](https://github.com/joyspinch/zan-lang/commit/1c586f33d5f62cb835305cbbe6e2c75128b73c7e)（提交说明原文："Xiangqi: 10 endgame drills, **gpt-image** wood/piece textures; gomoku real stone/board textures"；该木纹图随后被五子棋与围棋共用同一张）。
  - `stone_black.png` / `stone_white.png` / `title.png` —— [zan-lang `765e6685`](https://github.com/joyspinch/zan-lang/commit/765e66859190d4533b98cec10edde426256afbd1)（"Add gomoku (wood parlor, 3-tier AI, rank progression)"）。
  - `board_wood2.png` / `stone_black2.png` / `stone_white2.png` / `panel.png` —— [zan-lang `a00646ae`](https://github.com/joyspinch/zan-lang/commit/a00646ae9116bc90d44bd9bd95715d91e4e3bae9)（"gomoku: 手绘素材接入"，手绘风格即共享风格串里的 `hand-painted digital illustration`）。
- 仓库不含任何第三方版权素材；全部位图均为本项目自产（图像模型生成或本地程序化生成）。

## 许可

本仓库采用 [MIT 许可](LICENSE)。依赖的 zan-lang 仓库采用 ZCSL（Zan Community Source License 1.0）。

## 更多文档

- [`PROJECT.md`](PROJECT.md) —— 完整设计与实现说明
- [`client/README.md`](client/README.md) —— 客户端侧说明
