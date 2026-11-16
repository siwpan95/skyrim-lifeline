#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""frostwords CLI 回归（纯 stdlib，直接跑看退出码）。

    python tests/cli_check.py

设计要点：
    · 子进程统一 [sys.executable, "-X", "utf8", CLI] + UTF-8 解码，
      不受控制台代码页影响。
    · 垫片契约做**字节级**断言：可 ASCII 解码、裸 LF=0、孤立 CR=0、
      调用行加引号、含标记。
    · 完整性校验重算内容（解析导出的 JSON / 检查文本），不是只看文件在不在。
    · 退出码 0 / 1 / 2 / 6 / 130 各有一次触发；转发命令原样返回子进程码。
    · 需外部前提的用例记 SKIP 且**不计入通过数**。
"""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
CLI = TOOLS / "frostwords_cli.py"
PY = sys.executable

PASS: list[str] = []
FAIL: list[str] = []
SKIP: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        PASS.append(name)
    else:
        FAIL.append(f"{name}: {detail}")


def run(args, cwd=None, env=None, timeout=180):
    full_env = dict(os.environ)
    if env:
        full_env.update(env)
    cp = subprocess.run(
        [PY, "-X", "utf8", str(CLI), *args],
        cwd=str(cwd or ROOT), env=full_env,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=timeout,
    )
    return cp.returncode, cp.stdout, cp.stderr


def shim_bytes(path: Path) -> dict:
    sys.path.insert(0, str(TOOLS))
    import cli_shim
    return cli_shim.inspect_shim(path)


# ── ① 顶层命令面 ───────────────────────────────────────────────
def test_top() -> None:
    rc, so, _ = run(["--version"])
    check("--version rc=0", rc == 0 and "frostwords" in so, f"rc={rc} out={so!r}")
    rc, so, _ = run([])
    check("裸调用打帮助 rc=0", rc == 0 and "export-run" in so, f"rc={rc}")
    rc, so, _ = run(["--help"])
    check("--help rc=0", rc == 0 and "命令:" in so, f"rc={rc}")
    for cmd in ("export-run", "export-outline", "cases", "play", "verify",
                "install-cli", "uninstall-cli"):
        rc, so, _ = run([cmd, "--help"])
        check(f"{cmd} --help rc=0", rc == 0 and len(so) > 80, f"rc={rc}")
    rc, so, _ = run(["help", "export-run"])
    check("help <cmd> rc=0", rc == 0 and "完整导出" in so, f"rc={rc}")


# ── ② 退出码 2：用法错误 ───────────────────────────────────────
def test_usage() -> None:
    cases = [
        (["export-runn"], "未知命令"),
        (["export-run", "--format", "xml"], "未知格式"),
        (["export-run", "--ending", "end-nope"], "未知结局"),
        (["export-run", "--seed", "0"], "--seed"),
        (["export-run", "--script", "1,1", "--ending", "end-whiterun"], "互斥"),
        (["export-run", "--all-endings", "--script", "1,1"], "--all-endings"),
        (["export-run", "--bogus"], "unrecognized"),
    ]
    for args, needle in cases:
        rc, so, se = run(args)
        check(f"用法错误 rc=2 {args[:2]}",
              rc == 2 and (needle in so or needle in se),
              f"rc={rc} stdout={so[:80]!r} stderr={se[:120]!r}")
    rc, _, se = run(["export-runn"])
    check("未知命令带拼写建议", "export-run" in se, se[:120])


# ── ③ 全局选项两种位置 / -- 透传 ───────────────────────────────
def test_global_flags() -> None:
    rc1, a, _ = run(["--json", "cases"])
    rc2, b, _ = run(["cases", "--json"])
    check("--json 前置 rc=0", rc1 == 0, f"rc={rc1}")
    check("--json 后置 rc=0", rc2 == 0, f"rc={rc2}")
    check("--json 两种位置结果一致", a.strip() == b.strip(), "输出不同")
    try:
        data = json.loads(a)
        check("--json 是可解析 JSON 且 9 结局",
              data.get("ok") and data.get("count") == 9, str(data)[:120])
    except Exception as exc:
        check("--json 是可解析 JSON 且 9 结局", False, str(exc))
    rc, so, _ = run(["-q", "cases"])
    check("-q 抑制 [OK]/[INFO]", rc == 0 and "[OK]" not in so and "[INFO]" not in so,
          so[:120])

    # -- 之后原样落在 argv 末尾（不起真实子进程）
    sys.path.insert(0, str(TOOLS))
    import frostwords_cli as fw
    captured = {}
    orig = fw.subprocess.call

    def fake_call(argv, *a, **kw):
        captured["argv"] = list(argv)
        return 7

    fw.subprocess.call = fake_call
    try:
        rc = fw.dispatch("play", ["--", "--input", "1,1"], fw.Options())
    finally:
        fw.subprocess.call = orig
    check("-- 透传 argv 末尾", captured.get("argv", [])[-2:] == ["--input", "1,1"],
          str(captured))
    check("转发命令原样返回子进程码 7", rc == 7, f"rc={rc}")


# ── ④ 垫片字节契约 ─────────────────────────────────────────────
def test_shims() -> None:
    sys.path.insert(0, str(TOOLS))
    import cli_shim as S

    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        for name in S.NAMES:
            S.write_shim(d / name, 'set "FW_ROOT=%~dp0"')
        # 生成一份"绝对 root"垫片，验证两份只差 root 行
        abs_path = d / "frostwords_abs.cmd"
        S.write_shim(abs_path, S.root_line_for(ROOT))
        for name in S.NAMES:
            p = d / name
            r = shim_bytes(p)
            check(f"{name} ASCII / CRLF 合法",
                  r["ascii"] and r["bare_lf"] == 0 and r["lone_cr"] == 0,
                  str(r))
            check(f"{name} 调用行加引号 + 标记",
                  r["quoted_call"] and r["marker"], str(r))
        a = (d / S.NAMES[0]).read_bytes().decode("ascii").splitlines()
        b = abs_path.read_bytes().decode("ascii").splitlines()
        diff = [(x, y) for x, y in zip(a, b) if x != y]
        check("两份垫片仅 root 行不同", len(diff) == 1 and "FW_ROOT" in diff[0][0],
              str(diff))
        # 真 encode("ascii") 兜底断言（inspect 内部已 decode，这里再钉一次）
        raw = (d / S.NAMES[0]).read_bytes()
        try:
            raw.decode("ascii")
            ascii_ok = True
        except UnicodeDecodeError:
            ascii_ok = False
        check("垫片字节可 ASCII 解码", ascii_ok)


# ── ⑤ 导出完整性（重算内容，不是只看文件存在）──────────────────
def test_export() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        rc, so, se = run(["export-run", "--ending", "end-whiterun",
                          "--format", "all", "--output", str(d / "run")])
        check("export-run 三格式 rc=0", rc == 0, f"rc={rc} {se[:120]}")
        files = {f: d / f"run.{f}" for f in ("md", "json", "html")}
        for fmt, p in files.items():
            check(f"{fmt} 文件已生成", p.exists() and p.stat().st_size > 1000,
                  str(p))
        if files["json"].exists():
            data = json.loads(files["json"].read_text(encoding="utf-8"))
            check("JSON 步数 > 40 且结局正确",
                  data["meta"]["step_count"] > 40
                  and data["meta"]["final_scene"] == "end-whiterun",
                  str(data["meta"])[:160])
            check("JSON 每步都带状态快照",
                  all("state" in s and "changes" in s for s in data["steps"]))
            check("JSON 输入次数 >= 场景步数",
                  data["meta"]["input_count"] >= data["meta"]["step_count"],
                  str(data["meta"])[:160])
            # ── 对话话题采集（缺口补齐）─────────────────────
            dlg = [s for s in data["steps"] if s.get("mode") == "dialogue"]
            check("存在 dialogue 场景步", len(dlg) > 0, f"dialogue={len(dlg)}")
            check("每个对话步都带可见话题列表",
                  all(s.get("topics") for s in dlg),
                  str([s.get("scene") for s in dlg if not s.get("topics")])[:160])
            check("每个对话步都带逐轮编号基准快照",
                  all(s.get("topic_snapshots") for s in dlg),
                  str([s.get("scene") for s in dlg if not s.get("topic_snapshots")])[:160])
            # 话题编号必须从 1 连续，且与快照里的编号基准一致
            idx_ok = all(
                [t["index"] for t in s["topics"]] == list(range(1, len(s["topics"]) + 1))
                for s in dlg
            )
            check("可见话题编号从 1 连续重排", idx_ok)
            snap_ok = all(
                all([t["index"] for t in sn["topics"]]
                    == list(range(1, len(sn["topics"]) + 1))
                    for sn in s["topic_snapshots"])
                for s in dlg
            )
            check("每轮快照的编号基准同样连续", snap_ok)
            # 快照数量应与该场景的输入数一致（每次提问留一份）
            cnt_ok = all(
                len(s["topic_snapshots"]) == len(s["inputs"]) for s in dlg
            )
            check("快照数 == 该场景输入数", cnt_ok,
                  str([(s["scene"], len(s["topic_snapshots"]), len(s["inputs"]))
                       for s in dlg])[:200])
            # 已问过的话题必须保留占编号（引擎 visible() 语义）
            asked_ok = True
            for s in dlg:
                for sn in s["topic_snapshots"]:
                    asked_ids = {t["id"] for t in sn["topics"] if t.get("asked")}
                    if asked_ids and len(asked_ids) != len(
                        [t for t in sn["topics"] if t.get("asked")]
                    ):
                        asked_ok = False
            check("已问话题标记与话题集合一致", asked_ok)
        if files["md"].exists():
            md = files["md"].read_text(encoding="utf-8")
            check("Markdown 含终局状态表与结局 ID",
                  "终局状态" in md and "end-whiterun" in md and "状态变化" in md)
            check("Markdown 含对话话题段落",
                  "当时可见的话题" in md and "编号基准" in md)
        if files["html"].exists():
            ht = files["html"].read_text(encoding="utf-8")
            check("HTML 含 doctype / 折叠状态块",
                  "<!doctype html>" in ht and "<details>" in ht)
            check("HTML 含对话话题段落",
                  "当时可见的话题" in ht and "编号基准" in ht)

        rc, so, se = run(["export-outline", "--output", str(d / "outline.md")])
        check("export-outline rc=0", rc == 0, f"rc={rc} {se[:120]}")
        if (d / "outline.md").exists():
            ol = (d / "outline.md").read_text(encoding="utf-8")
            check("大纲含全部场景标题", ol.count("\n## `") == 113,
                  str(ol.count("\n## `")))
            check("大纲出边表带条件列", "| 条件 |" in ol)


# ── ⑥ 退出码 1 / 6 / 130 ───────────────────────────────────────
def test_other_codes() -> None:
    # 1：父路径是普通文件 → 写失败
    blocker = ROOT / "tests" / "e2e_cases.json"
    rc, _, se = run(["export-run", "--ending", "end-whiterun", "--format", "md",
                     "--output", str(blocker / "impossible.md")])
    check("写失败 rc=1", rc == 1, f"rc={rc} {se[:160]}")

    # 6：PYTHONPATH 注入一个会抛错的假 dse_core，模拟环境缺失
    with tempfile.TemporaryDirectory() as tmp:
        fake = Path(tmp) / "dse_core"
        fake.mkdir()
        (fake / "__init__.py").write_text('raise ImportError("injected")\n',
                                          encoding="utf-8")
        rc, so, se = run(["cases"], env={"PYTHONPATH": tmp})
        check("环境缺失 rc=6", rc == 6, f"rc={rc} stdout={so[:100]!r} stderr={se[:160]!r}")

    # 130：中断（无法真按 Ctrl-C，用 monkeypatch 触发同一条异常路径）
    sys.path.insert(0, str(TOOLS))
    import frostwords_cli as fw
    orig = fw.dispatch

    def boom(*a, **kw):
        raise KeyboardInterrupt()

    fw.dispatch = boom
    try:
        rc = fw.main(["cases"])
    finally:
        fw.dispatch = orig
    check("中断 rc=130", rc == 130, f"rc={rc}")


# ── ⑦ 装 / 卸回归（他人同名文件必须保留）──────────────────────
def test_install_uninstall() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        rc, so, se = run(["install-cli", "--shim-dir", str(d), "--dry-run"])
        check("install --dry-run rc=0", rc == 0 and "would write" in so,
              f"rc={rc} {so[:120]}")
        check("dry-run 不写目标文件", not (d / "frostwords.cmd").exists())

        rc, so, se = run(["install-cli", "--shim-dir", str(d), "--no-root", "-q"])
        check("install rc=0", rc == 0 and (d / "frostwords.cmd").exists(),
              f"rc={rc} {se[:120]}")

        # 把其中一个换成「他人手工文件」
        manual = d / "fwcli.cmd"
        manual.write_text("rem hand written, do not delete\r\n", encoding="ascii")
        rc, so, se = run(["uninstall-cli", "--shim-dir", str(d)])
        check("uninstall rc=0", rc == 0, f"rc={rc}")
        check("卸载只删带标记的文件",
              not (d / "frostwords.cmd").exists() and manual.exists(),
              f"剩余={[p.name for p in d.iterdir()]}")
        check("跳过项被列出", "跳过" in so, so[:160])


# ── ⑧ 退出码 0 的转发命令（真跑一次）──────────────────────────
def test_passthrough() -> None:
    rc, so, se = run(["verify", "--fast"], timeout=240)
    check("verify 转发 rc=0", rc == 0 and "全部门禁通过" in so,
          f"rc={rc} {se[:120]}")


def main() -> int:
    for fn in (test_top, test_usage, test_global_flags, test_shims,
               test_export, test_other_codes, test_install_uninstall,
               test_passthrough):
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            FAIL.append(f"{fn.__name__} 抛异常: {type(exc).__name__}: {exc}")
    print(f"PASS {len(PASS)}  FAIL {len(FAIL)}  SKIP {len(SKIP)}")
    for f in FAIL:
        print(f"  [FAIL] {f}")
    if SKIP:
        for s in SKIP:
            print(f"  [SKIP] {s}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
