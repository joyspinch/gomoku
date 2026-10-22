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
- 其余素材（木纹棋盘、棋子、标题图）随 zan-lang 早期游戏模板一同迁出，**仍没有留下来源与授权记录**；公开发布前请自行核对这些素材的授权，或按同样方式改成本地生成。

## 许可

本仓库采用 [MIT 许可](LICENSE)。依赖的 zan-lang 仓库采用 ZCSL（Zan Community Source License 1.0）。

## 更多文档

- [`PROJECT.md`](PROJECT.md) —— 完整设计与实现说明
- [`client/README.md`](client/README.md) —— 客户端侧说明
