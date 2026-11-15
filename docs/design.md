# 霜语 · 设计文档

> 《霜语》(Frostwords) —— 一个上古卷轴同人纯文字生存叙事
> 参考对象：《生命线》(Lifeline) 系列（3 Minute Games, 2015–）
> 引擎：[dse-core](https://pypi.org/project/dse-core/) 字典场景引擎（Python 版 / cordis-py）

---

## 一、为什么是这个结构

《生命线》的核心不是"文字游戏"，而是**三个反直觉的设计**：

| # | 生命线的设计 | 为什么重要 |
|---|---|---|
| 1 | **玩家不能直接操作主角** | 玩家只能"给建议"，主角决定听不听 → 玩家的输入是**影响**而非**控制** |
| 2 | **主角会拒绝你的建议** | 破坏玩家的掌控感，制造"她有自己的意志"的不安 |
| 3 | **死亡是常见的，Rewind 是免费的** | 失败不惩罚，反而鼓励重试 → 探索成本趋近于零 |

本作把这三点作为**地基**，其余一切（雪原、龙焰、诺德人的丧俗）都是皮。

---

## 二、机制映射表：生命线 → DSE 原生能力

**核心约束**：`dse-core` 的 `Scene` JSON Schema 是**封闭**的
（`additionalProperties: false`，`mode` 枚举固定为 5 个值）。
实测塞入自定义字段 `consult:` 会被 `dse check` 直接打回：

```
./content/t.yml start: Additional properties are not allowed ('consult' was unexpected)
./content/t.yml start/mode: 'consult' is not one of ['normal', 'battle', 'trade', 'diary', 'dialogue']
```

所以**没有自定义 mode 这条路**。所有机制必须用引擎已有的五种模式 + 数据表达实现。

| 生命线机制 | DSE 实现 | 具体写法 |
|---|---|---|
| 玩家给建议，主角决定听不听 | **加权随机 goto**（P6） | `goto: [{to: 遵守, weight: 7}, {to: 违抗, weight: 3}]` |
| 消息历史可回看 | **diary 模式** | `mode: diary` + `diary.onExit`，回看所有已读场景 |
| 主角主动提问 / 玩家有限的注意力 | **dialogue 模式** | `dialogue.notes` = 注意点预算，话题有 `if` 可见性门槛 |
| 战斗 | **battle 模式** | `battle: {enemy, onWin, onLose, onFlee}` |
| 补给与取舍 | **trade 模式** | `trade: {days, onEnd}` + 确定性行情表 |
| 文本随状态变化 | **extraText**（P6） | 条件文本段，`if` 为真才拼接 |
| 同一场景的不同措辞 | **variants**（P6） | `variantMode: cycle` 按访问次数轮转 |
| 选项只出现一次 | **once**（P8） | `once: '稳定键'`（推荐自定义键，防热更漂移） |
| Rewind（回到上次选择点） | **rollback 命令**（P9） | `rollback [n]` / `rb` / `back` |
| 重开一局 | **@restart** | 特殊 goto 目标，全量重置状态 |
| 玩家可选的支线 | **tunnels**（P8） | `goto: {call: x}` + 被调场景 `@return` |
| 成就 | **achievements 插件** | `scene/enter` + `choice/made` 事件驱动 |
| 随机可复现 | **engine.seed** | `dse.yml` 里 `engine.config.seed` 固定加权随机 |

### 2.1 「她有时会拒绝你」的具体写法

这是全作最重要的机制。核心场景 `core-advice-1`：

```yaml
core-advice-1:
  title: 序章 · 第一个建议
  text: |
    「两天，也许三天。我从海尔根爬出来之后就一直在走……」
    「你说往东——东边是什么？」
  choices:
    - text: 「东边是缓坡，有猎人小屋，有火。」
      do: { soul: -1, trust: +2 }
      goto:
        - { to: core-east-obey, weight: 7 }   # 她照做
        - { to: core-east-defy, weight: 3 }   # 她拒绝
```

两条支路**都汇入 `core-ask`**（下一节拍），只在过程上分岔 ——
这是路径数控制的关键（见 §四）。

她的台词差异放在各自场景里，而**状态影响**（如 `flags.refusedAdvice`、
`trust: -2`）写在支路场景的 `onEnter`，由 `extraText` 在后续场景里显现。

---

## 三、状态模型

`dse.yml` 的 `state.initial` 是**唯一真源**。铁律：

> **条件表达式（`if:`）里用到的每个顶层字段，必须在 `initial` 里预声明。**
> 否则求值时 NameError → `state.check` 兜底判 False → 表现为「选项莫名不出现」，
> 极难排查。同理，`flags.*` / `clues.*` / `items.*` 里被引用的键也要预声明。

| 字段 | 含义 | 设计意图 |
|---|---|---|
| `trust` | 她对你的信任 0–100 | 决定真结局门槛（≥65）、龙吼结局（≥75）、以及她听不听你的倾向 |
| `soul` | 灵魂水晶余量 | 每次深度咨询消耗 1；归零即通讯断绝 |
| `warmth` | 体温 0–100 | **唯一硬死亡线**。每场景自然下降，篝火/食物回升，≤12 触发冻死结局 |
| `hp` | 生命值 | 战斗与龙焰灼烧消耗 |
| `clues.*` | 线索库 | **知识即选项**：知道龙吼（`thuUm`）才能解锁战术优势选项 |
| `flags.*` | 剧情旗标 | 决定结局分流（如 `sawDragon`、`keptSecret`） |

### 3.1 数值护栏与硬性失败分支（dse-core 0.7.0 反哺）

骨架阶段的状态会越界：〔本机〕一条真结局路径终局曾出现
`hp=-38 / soul=-22 / trust=129`，负数血量与超界信任只是躺在状态里，
不参与结局判定 —— 玩家照样能选到真结局。0.7.0 在引擎侧补了两类声明式护栏，
本仓在 `dse.yml` 的 `state` 段使用：

- **`bounds`**：每处 `onEnter` / 选项 `do` 结算后自动钳进区间，`max` 可引用
  另一字段（`hp.max → maxHp`）。本作给 `hp / stamina / warmth / soul / trust /
  rations / gold` 七个字段声明了 0 上下的区间。钳制**不改变条件真假语义** ——
  `end-select` 的 `hp<=4` / `trust>=75` 门槛在钳制前后同样成立，8 结局可达性不变。
- **`fatal`**：命中即正规改道到目标场景，先于渲染与结局判定。本作只设一条
  早期体温线 `warmth <= 0 and clock <= 8 → end-frozen`：第一章体温归零是玩家
  连选暴露风雪路线的真实可避失败态。终局分流的 `warmth<=12 → end-frozen` 仍保留，
  二者不冲突（8 条通关路径体温只在 `clock>=17` 才归零，不触发早期线）。
  **刻意不设 `hp<=0` fatal**：终局有「惨胜」路径以 `hp=0` 收尾，硬改道会误杀
  正当通关；重伤/死亡由 `end-select` 的 `trust>=55 and hp<=4 → end-mercy` 表达。

〔本机 `@SIWPAN` 时点实测〕钳制后真结局终局
`hp=0 / soul=0 / stamina=0 / trust=100 / warmth=7 / clock=20`，全部落在合法区间。
换机 / 升级运行时后数值须现场复测，不作跨机结论。

---

## 四、路径爆炸：一个必须记录在案的工程约束

### 4.1 现象

`dse traverse` 是**穷举 DFS**：路径数 = 路径上各节点出度之**乘积**。
对本作（分支因子 2–3、深度 78）做静态路径计数，得：

```
从 core-open 出发的完整路径总数: 23,684,099,052,771,442,911,358,656,000  (2.37e+28)
```

`dse traverse` 跑了 **7 分半未完成**（已终止），因为它要枚举 10²⁸ 条路径。

### 4.2 实测基准（合成图，验证上述公式）

| 场景链深度 | 分支形态 | 路径数 | traverse 耗时 |
|---|---|---|---|
| 6 | 3 选项同目标 | 729 | 0.02s |
| 10 | 3 选项同目标 | 59,049 | 1.12s |
| 14 | 3 选项同目标 | 4,782,969 | 88.38s |
| 6 | 2 选项不同目标 | 64 | 0.01s |
| 10 | 2 选项不同目标 | 1,024 | 0.04s |
| 14 | 2 选项不同目标 | 16,384 | 0.48s |

两个结论：

1. **路径数 ≈ 分支因子 ^ 深度**，指数墙是硬的。
2. **多个选项指向同一目标反而更慢** —— traverse 对每条边独立递归，
   3 条边指向同一节点会走 3 遍。

### 4.3 结论与对策

**任何分支叙事（分支因子 ≥2、深度 ≥20）在数学上都不可能跑完穷举 traverse。**
这不是内容写坏了，是 `traverse` 的设计不适用于大规模分支叙事。

引擎自己给了答案（其 README）：

```bash
dse coverage --e2e end-secret   # 声明某个结局已由 e2e 用例覆盖
```

所以本作的门禁分四层（见 `tools/verify.py`）：

| 层 | 工具 | 抓什么 | 耗时 |
|---|---|---|---|
| ① 静态 | `dse check` 等价 + 条件字段预声明门 | Schema 不符、悬空跳转、图连通性、旗标拼错 | 毫秒级 |
| ② 动态 fuzz | 真实引擎随机游走采样 | 条件恒假、表达式求值炸、效果写错、场景缺失 | 秒级 |
| ③ 端到端 | `dse test --script` 等价 | 整条通关路径的最终场景与状态断言 | 秒级 |
| ④ 结局覆盖 | `dse coverage --e2e` 等价 | 每个结局有 S（静态可达）或 E（e2e 回放）来源 | 毫秒级 |

### 4.3 为什么第 ② 层是采样，而不是「按章遍历」

一开始试过「按章 `traverse --entry` 分段」：`ch4-open` 单独遍历
= 4.3s / 11,556 条路径 / 零错误，看着可行。但从 `core-open` 或较深的
章节入口起步会**顺着主线走完全图** —— 实测 `ch1` 在 200 秒内都跑不完。
穷举 DFS 在任何分支叙事上都不可用，分段救不了它。

因此第 ② 层改为**随机游走采样（fuzz）**：订阅 `scene/enter`，每次进入
场景就往脚本输入队列头部注入一个该场景的合法输入，用真引擎跑 N 条随机
路径。引擎会拒绝非法输入并等待下一个，所以采样既能真实执行五种 mode，
又不会因路径组合爆炸而卡死。

实测〔本机 `@SIWPAN` 时点〕：200 条随机路径 / 覆盖 89/109 场景（82%）/
零异常（耗时 66.8s，时点值不作门禁断言）。步进上限（默认 80 场景）保证
每条样本必定终止 —— 结局场景带 `@restart` 选项，没有上限就会不停重开。

### 4.4 进程级环境隔离（踩过的坑，0.7.0 已根治）

老版 `dse_core.sdk.create_engine(entry=...)` 会把 `DSE_ENTRY` 写进 `os.environ`
且**从不清理**。fuzz 按章起步后残留的 `DSE_ENTRY` 会让后续 e2e 从错误
入口开始 —— 输入流整体错位，表现为「全部用例莫名停在中途的 `ch4-*`
场景」。0.7.0 改为把 `entry` 注入 engine config，不再污染进程环境；
`verify.py` 仍保留显式 `os.environ.pop("DSE_ENTRY")`，作为跨版本兼容的保险。

另：老版 combat 插件用全局 `random.random()`，不受 `engine.rng` 控制。
0.7.0 改用 `engine.rng`，随机源已隔离。`verify.py` / `solve_e2e.py`
目前**同时固定 `engine.rng` 与全局种子** —— 这样同一套脚本在 0.6.x 与
0.7.0 上都能复现。升级 0.7.0 后战斗结果变化导致旧 e2e 输入流整体错位
（实测 7/8 停在 `ch2-tavern`），已用 `solve_e2e.py --all --write-cases`
重建全部 8 条用例。

### 4.5 内容层的结构约束（写新内容时建议遵守）

1. **藤蔓而非线形**：一个节拍的多条支路应在 1–2 跳内汇入同一后继。
   支路只改变**过程**（`onEnter` 效果、`extraText` 差异），不复制**下游**。
2. **加权分支同理**：`obey`/`defy` 两条支路尽量汇入同一后继场景。
3. **同目标多选项要少用**：3 选项同目标 = 3 倍路径。

> 这些不再影响门禁能否跑完（门禁已改为采样 + e2e），但会让剧情图
> 更易读、让 replay 与人工排查更可控。

---

## 五、结局设计

八个结局，由 `end-select` 一个闸门按状态**并列呈现**，玩家在最后一步亲自选。
条件满足的结局都会出现在选项里，最后一条是无条件兜底 —— 这保留了《生命线》
「最后一按由你负责」的味道，而不是替玩家自动判定。

| 结局 | 触发条件 | 类型 |
|---|---|---|
| `end-refused` | `trust < 20` | 断线（最低优先级兜底） |
| `end-mercy` | `trust >= 55 and hp <= 4` | 翻转：她死了，但事办成了 |
| `end-thu-um` | `trust >= 75 and clues.thuUm and flags.knewTruth` | **隐藏真结局**（龙吼） |
| `end-soldiers` | `flags.bribedGuard and not flags.keptSecret` | 被举报告发 |
| `end-frozen` | `warmth <= 12` | 冻死 |
| `end-dragon` | `flags.sawDragon and flags.refusedAdvice` | 被龙吞 |
| `end-whiterun` | `trust >= 65` | **真结局** |
| `end-alone` | `trust >= 40` | 她独自走完 |
| `end-refused`（兜底） | 以上皆不满足 | 断线 |

### 5.1 结局场景只能有 `@` 目标选项

引擎的 `graph.is_ending` 判定：

```python
def is_ending(scene) -> bool:
    if not scene: return False
    if scene.get("mode") and scene["mode"] != "normal": return False
    choices = scene.get("choices") or []
    return len(choices) == 0 or all(str(c.get("goto") or "").startswith("@") for c in choices)
```

**普通 `goto` 选项会让场景失去结局身份**，coverage 门禁统计不到它。

本作的做法：8 个结局场景各带**一个** `「（重新开始。）」→ @restart` 选项。
因为所有选项都是 `@` 目标，`is_ending` 仍为真；同时玩家通关后有直接重开的
出口，不需要额外的公共枢纽。早期版本曾设 `end-restart` / `end-restart-stay`
枢纽，但结局场景一旦无选项就没有任何入边指向它们 → 变成 `dse check`
告警的孤儿场景，现已移除，尾声文案并入 `end-whiterun` 正文。

---

## 六、剧情结构

```
序章 core      灵魂链接建立；教学（加权分支 / dialogue / diary）
第一章 ch1     风隘雪原：体温压力、霜狼战斗、灰烬渡口补给
第二章 ch2     白漫之下：守卫谈判、法师真相、霜尸鬼、猎龙人支线
第三章 ch3     龙临堡：拔根之战、幼龙决战、最后的承诺
第四章 ch4     白漫城下：追兵、两条政治线、最终抉择
结局 endings   分流闸门 + 八个结局（各自带 @restart 出口）
```

内容包按剧情顺序在 `dse.yml` 的 `scenes.packs` 里列出（后者覆盖前者同 ID 场景）。

---

## 七、待办 / 后续扩展

- [x] **数值平衡（0.7.0 反哺已完成，见 §3.1）**：`state.bounds` 钳制七个
      数值字段、`state.fatal` 早期体温失败分支，终局数值落在合法区间；
      8 结局可达性经全量门禁复验不变。
- [ ] `end-dragon-slayer` 结局补齐（战斗胜利后的独立分支）
- [ ] 更多 `variants` 变体文本（提升重玩观感）
- [ ] `i18n` 插件接入（英译）
- [ ] HTML 单文件导出（`dse export-html` 仅支持 normal 模式，需拆分战斗/对话场景）
- [ ] 成就系统补全（当前 6 条）
- [ ] 美术：终端 ASCII 头像 / 地图
