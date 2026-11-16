#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""霜语 · e2e 脚本求解器（真实引擎试错法）。

为什么不用「手写模拟引擎语义」的办法？
────────────────────────────────────────
手写模拟必然漏细节 —— 本项目开发过程中实际踩到的坑：
    · dialogue 的 do_ask 检查顺序是「已问过」在前、「注意点用尽」在后
      → 用已问过的话题永远触发不了结束，对话卡死
    · trade 的 next_day()：days=2 需要**两次** next 才收市
    · battle 是**多回合**的：一次 a 只打一部分血，敌人会反击
每一条都得跟引擎源码对齐，稍有偏差就产出「看起来对但跑不通」的假脚本。

所以本工具**不模拟**：直接用真实引擎跑，每一步试所有候选输入，
看哪个落点最能推进目标条件。慢一点，但产出的脚本**必然**可跑。

代价：每步都要重跑一遍引擎（O(步数²)）。对本作（~60 步）完全够用。

用法：
    python tools/solve_e2e.py --target end-whiterun
    python tools/solve_e2e.py --all
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dse_core.loader import load_project                     # noqa: E402
from dse_core.sdk import create_engine                       # noqa: E402

SEED = 20261115


# ── 目标结局的达成条件（与 content/50-endings.yml 保持一致）───
GOALS: dict[str, list[tuple[str, object]]] = {
    "end-refused": [
        ("trust < 20", lambda s: (s.get("trust") or 0) < 20),
    ],
    "end-alone": [
        ("trust >= 40 且 trust < 65", lambda s: 40 <= (s.get("trust") or 0) < 65),
    ],
    "end-whiterun": [
        ("trust >= 65", lambda s: (s.get("trust") or 0) >= 65),
    ],
    "end-thu-um": [
        ("trust >= 75", lambda s: (s.get("trust") or 0) >= 75),
        ("clues.thuUm", lambda s: bool((s.get("clues") or {}).get("thuUm"))),
        ("flags.knewTruth", lambda s: bool((s.get("flags") or {}).get("knewTruth"))),
    ],
    "end-dragon": [
        ("flags.sawDragon", lambda s: bool((s.get("flags") or {}).get("sawDragon"))),
        ("flags.refusedAdvice", lambda s: bool((s.get("flags") or {}).get("refusedAdvice"))),
    ],
    "end-frozen": [
        ("warmth <= 12", lambda s: (s.get("warmth") or 999) <= 12),
    ],
    "end-soldiers": [
        ("flags.bribedGuard", lambda s: bool((s.get("flags") or {}).get("bribedGuard"))),
        ("not flags.keptSecret", lambda s: not bool((s.get("flags") or {}).get("keptSecret"))),
    ],
    "end-mercy": [
        ("trust >= 55", lambda s: (s.get("trust") or 0) >= 55),
        ("hp <= 4", lambda s: (s.get("hp") or 999) <= 4),
    ],
    "end-dragon-slayer": [
        ("flags.absorbedSoul", lambda s: bool((s.get("flags") or {}).get("absorbedSoul"))),
        ("trust >= 60", lambda s: (s.get("trust") or 0) >= 60),
    ],
}


# ── 候选输入（只按场景声明列合法输入，不猜引擎语义）────────────
def _visible_by_if(items: list, snapshot: dict) -> list:
    """按引擎口径过滤 `if`：evaluate 对快照求值，异常兜底 False。"""
    from dse_core.safety import evaluate
    out = []
    for item in items:
        cond = item.get("if")
        ok = True
        if cond:
            try:
                ok = bool(evaluate(cond, snapshot))
            except Exception:
                ok = False  # 与引擎 check 的异常兜底 False 一致
        if ok:
            out.append(item)
    return out


def candidates_for(scene: dict, mode: str, snapshot: dict | None = None) -> list[str]:
    snap = snapshot or {}
    if mode == "normal":
        # ★ 0.3.1：引擎 render 只渲染 if 为真的选项并重编号；此前按原始
        #   choices 全量编号会与门控选项错位（求解器靠「非法输入原地不动」
        #   歪打正着跳过，但语义不可靠）。改为与引擎一致的可见列表口径。
        return [str(i + 1) for i, _ in
                enumerate(_visible_by_if(scene.get("choices") or [], snap))]
    if mode == "battle":
        return ["a", "d", "r"]
    if mode == "dialogue":
        dlg = scene.get("dialogue") or {}
        topics = dlg.get("topics") or []
        asked = set(snap.get("dialogueAsked") or [])
        # ★ 0.3.1：引擎 do_ask 的编号来自 visible()——先按 `if` 过滤、
        #   再 enumerate 重排。此前这里按原始 topics 全量编号，遇到门控话题
        #   （如 core-ask 的 why/listener）会与引擎口径错位，产出的 ask N
        #   语义名不副实（歪打正着能跑通，但一旦改门槛就崩）。
        visible = [t for t in _visible_by_if(topics, snap)
                   if t.get("id") not in asked]
        outs = [f"ask {i + 1}" for i, _ in enumerate(visible)]
        # ★ 0.3.1：注意点用尽后，引擎会把任何 ask 当作「用尽→结束」消费，
        #   那是假提问；此时只给 end 收尾，避免录进无效输入、也避免 end 溢出
        #   到下一场景。未用尽时保留 ask 在前（带信任等效果、分数更高会被选中），
        #   end 殿后，保证对话内容不会被过早跳过。
        notes = dlg.get("notes") or 0
        if notes > 0:
            topic_ids = {t.get("id") for t in topics}
            used_here = len(topic_ids & asked)
            if used_here >= notes:
                return ["end"]
        outs.append("end")
        return outs
    if mode == "trade":
        return ["next"]
    if mode == "diary":
        return ["back"]
    return []


# ── 真实引擎试跑 ───────────────────────────────────────────────
def run(script: list[str], seed: int = SEED) -> tuple[str, dict]:
    """用真实引擎跑一段脚本，返回 (最终场景, 状态快照)。

    ★ 0.7.0 起 combat 走 engine.rng；老版用全局 random。两个种子都固定以
      兼容两种引擎，否则同一脚本两次跑会走出不同分支。
    """
    os.environ["DSE_INPUT"] = ",".join(script)
    buf = io.StringIO()
    try:
        ctx = create_engine(root=ROOT, quiet=True)
        engine = ctx.services["engine"]
        state = ctx.services["state"]
        engine.rng = random.Random(seed)
        random.seed(seed)
        with contextlib.redirect_stdout(buf):
            engine.start()
        return engine.current, state.snapshot()
    finally:
        os.environ.pop("DSE_INPUT", None)


def score(snapshot: dict, goals, target: str | None = None) -> float:
    """目标达成度。

    纯布尔目标在平局时没有方向感，因此给「越低越好」类目标补一个连续型
    奖励项，量级刻意压得很小（0~0.1），只用于打破平局，不会盖过
    「到达目标」的 1000 分。

    设计教训：早期 `end-dragon` 的条件写成 `sawDragon and trust < 45`，
    但全程只有 6 处 trust 减点（合计 -11）、增长点却极多（实测终局 129），
    该结局**静态可达、实际永远触发不了**。已改为
    `sawDragon and refusedAdvice`（两个都真实可达成）。
    """
    base = (sum(1 for _, f in goals if f(snapshot)) / len(goals)) if goals else 0.0
    if target == "end-frozen":
        w = snapshot.get("warmth")
        if isinstance(w, (int, float)):
            base += max(0.0, 100 - w) / 1000.0
    if target == "end-dragon-slayer":
        # 双目标（absorbedSoul + trust>=60）在平局时缺少朝 trust 的梯度，
        # 补一个 0~0.06 的连续项打破平局，量级远小于「到达目标」的 1000 分。
        t = snapshot.get("trust")
        if isinstance(t, (int, float)):
            base += min(t, 60) / 1000.0
    return base


def solve(target: str, max_steps: int = 90, verbose: bool = False,
          jitter: float = 0.0) -> list[str] | None:
    goals = GOALS.get(target)
    d = load_project(ROOT).dict
    rng = random.Random(SEED + int(jitter * 100000))

    script: list[str] = []
    for step in range(max_steps):
        cur, snap = run(script)
        if cur == target:
            return script
        sc = d.get(cur)
        if sc is None:
            return None
        mode = sc.get("mode") or "normal"
        cands = candidates_for(sc, mode, snap)
        if not cands:
            return None

        best = None
        best_val = -1e9
        for inp in cands:
            nxt, nsnap = run(script + [inp])
            # 输入被引擎拒绝 → 流程原地不动（同一场景、同一状态）→ 跳过
            if nxt == cur and nsnap == snap:
                continue
            val = ((1000.0 if nxt == target else 0.0)
                   + score(nsnap, goals, target)
                   + rng.random() * jitter)
            if val > best_val:
                best_val = val
                best = inp
                if best_val >= 1000.0:
                    break
        if best is None:
            return None
        script.append(best)
        if verbose:
            print(f"    步 {step:>2}: {cur:<22} 选 {best:<8} 分 {best_val:.2f}", file=sys.stderr)
    cur, _ = run(script)
    return script if cur == target else None


ENDINGS: dict[str, str] = {
    "end-whiterun": "真结局 · 走进白漫",
    "end-thu-um": "隐藏结局 · 龙吼",
    "end-mercy": "翻转结局 · 她死了，但事办成了",
    "end-refused": "结局 · 断线",
    "end-soldiers": "结局 · 被举报告发",
    "end-frozen": "结局 · 冻死在雪里",
    "end-dragon": "结局 · 被龙吞",
    "end-alone": "结局 · 她独自走完",
    "end-dragon-slayer": "结局 · 屠龙者",
}

# 与 content/50-endings.yml 的 end-select 条件一致；到达该结局即意味着
# 这些条件成立，因此可作为 e2e 的附加状态断言（防止脚本误入同名兜底）。
EXPECT: dict[str, list[str]] = {
    "end-whiterun": ["trust >= 65"],
    "end-frozen": ["warmth <= 12"],
    "end-thu-um": ["clues.thuUm"],
    "end-mercy": ["hp <= 4"],
    "end-dragon-slayer": ["flags.absorbedSoul"],
}


def write_cases(results: dict[str, list[str]]) -> Path:
    """把求解结果写成 verify.py 消费的 e2e 用例数据。"""
    cases = [{"name": ENDINGS.get(t, t),
              "script": ",".join(s),
              "expect_scene": t,
              "expect": EXPECT.get(t, [])}
             for t, s in sorted(results.items())]
    path = ROOT / "tests" / "e2e_cases.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cases, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
    return path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--max-steps", type=int, default=90)
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--write-cases", action="store_true",
                    help="把求解结果写入 tests/e2e_cases.json")
    args = ap.parse_args()
    targets = sorted(GOALS) if args.all else ([args.target] if args.target else [])
    if not targets:
        ap.error("需要 --target 或 --all")
    results: dict[str, list[str]] = {}
    for t in targets:
        script = solve(t, args.max_steps, args.verbose)
        if script is None:
            print(f"✗ {t:<22} 未找到路径")
            continue
        real, _ = run(script)
        if real != t:
            print(f"✗ {t:<22} 复现失败（实际 {real}）")
            continue
        results[t] = script
        print(f"✓ {t:<22} {len(script):>3} 步: \"{','.join(script)}\"")
    if results:
        print("\n--- E2E_CASES ---")
        for t, s in results.items():
            print(f'    {{"name": "{t}", "script": "{",".join(s)}", "expect_scene": "{t}"}},')
    if results and args.write_cases:
        path = write_cases(results)
        print(f"\n已写入 {len(results)} 条用例 → {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
