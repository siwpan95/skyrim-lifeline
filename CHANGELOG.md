# Changelog

本文件遵循 Keep a Changelog 结构，版本号遵循 SemVer。

## [Unreleased]

## [0.1.0] - 2026-11-15

### Added

- 7 个纯 YAML 内容包：**109 场景 / 8 结局 / 五种 mode**（normal / battle /
  dialogue / trade / diary），含加权随机建议、Rewind、消息历史与有限注意力谈判。
- `tools/verify.py` 四层门禁：静态校验与字段预声明门、真实引擎 fuzz 采样、
  8 条 e2e 通关回放、结局覆盖门。
- `tools/solve_e2e.py`：逐步用真实引擎试错求解通关输入流，产出
  `tests/e2e_cases.json`。
- `frostwords` CLI：完整流程导出（Markdown / JSON / HTML）、全场景静态大纲、
  Windows `.cmd` 垫片与 54 项回归。
- 文档：设计说明、Mermaid 场景图、序章试玩实录、CLI 手册、
  allin repocheck 实战校验报告。

### Notes

- 骨架阶段数值未平衡：终局资源可能为负，`trust` 未做 0–100 钳制，
  缺硬性死亡分支。详见 `docs/design.md`「待办」。
- `dse export-html` 只支持 `normal` 模式；完整可玩入口是 `dse play`。
- 文档中的绝对路径、解释器版本、仓数与字节数均为带机器名的时点事实，
  不是跨机器通用结论（见 `docs/allin-repocheck-validation.md` §0）。
