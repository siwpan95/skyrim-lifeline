#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""霜语 · 命令行入口（编排层）。

铁律：**CLI 不二次实现业务逻辑**。采集/渲染在 tools/export_run.py，
垫片在 tools/cli_shim.py，校验在 tools/verify.py，游戏在 dse play。
这里只做参数解析、前置校验、调用转发与退出码映射。

退出码契约：
    0   成功
    1   一般失败（引擎异常 / 写文件失败）
    2   用法错误（未知命令、参数非法、结局不存在）
    6   环境缺失（dse-core 未安装、工程文件缺失、找不到 Python）
    130 用户中断
    转发命令（play / verify）原样返回子进程退出码，不压成 1。

全局选项 --json / -q / --quiet 可出现在子命令前或后；
`--` 之后的一切原样透传给被启动的程序。
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

VERSION = "1.0.0"
DEFAULT_ENDING = "end-whiterun"
DEFAULT_SEED = 20261115
FORMATS = ("md", "json", "html")
COMMON_FLAGS = ("--json", "-q", "--quiet")

COMMANDS = ("export-run", "export-outline", "cases", "play", "verify",
            "install-cli", "uninstall-cli", "help")

HELP = """\
frostwords - 霜语 · Frostwords 命令行工具

用法:
  frostwords [全局选项] <命令> [参数...]
  frostwords <命令> --help          查看某个命令的详细说明

命令:
  export-run       完整导出一次游戏流程（真实引擎逐场景采集）
  export-outline   导出全部场景的静态流程大纲（当前 113 个）
  cases            列出可用结局及其通关脚本（当前 9 个）
  play             转发到 dse play（参数原样透传）
  verify           转发到 tools/verify.py（四层门禁）
  install-cli      生成 .cmd 垫片并安装到 PATH 目录
  uninstall-cli    卸载 PATH 垫片（仓库根垫片保留）
  help <命令>      查看详细帮助

全局选项:
  --json           把结果摘要以 JSON 打印到 stdout（转发命令 play/verify 不支持）
  -q, --quiet      只打印错误
  --version        显示版本
  -h, --help       显示本帮助

最常用:
  frostwords export-run --ending end-whiterun --format md,json,html
  frostwords export-run --all-endings
  frostwords cases
  frostwords install-cli

退出码: 0 成功 / 1 一般失败 / 2 用法错误 / 6 环境缺失 / 130 中断
"""

HELP_DETAIL = {
    "export-run": """\
frostwords export-run - 完整导出一次游戏流程

从真实引擎逐场景采集：场景正文、当时可见的选项、玩家的每一次输入、
相邻场景的状态变化、终局状态。五种 mode 的多回合/连问/逐日都会记录。

参数:
  --ending ID        选用 tests/e2e_cases.json 里已验证的通关脚本
                     （默认 end-whiterun；用 `frostwords cases` 查看全部）
  --script STR       自定义输入流（逗号分隔），与 --ending 互斥
  --format LIST      导出格式：md / json / html / all，或逗号组合
                     （默认 md）
  --output PATH      输出文件；多格式时按 stem 加各自后缀
                     （默认 exports/playthrough-<结局>.<后缀>）
  --seed N           随机种子，正整数（默认 20261115）
  --all-endings      为全部 9 个结局各导出一份（忽略 --output / --script）

说明:
  · 采集全程跑真实引擎，只是旁听 scene/enter 与 io.ask，不参与推进，
    因此导出的流程与 dse play 一致。
  · 改动内容包后请先重跑 tools/solve_e2e.py --all --write-cases，
    否则旧脚本的选项编号会漂移。

示例:
  frostwords export-run
  frostwords export-run --ending end-thu-um --format all
  frostwords export-run --script "1,1,1,ask 1,a,a,next,next" --output /tmp/run.md
""",
    "export-outline": """\
frostwords export-outline - 导出全场景静态流程大纲

列出全部场景、模式、每条出边的目标/类型/条件/选项文本/权重。
这是「所有可能分支」的大纲，不是某一局的实际走法。

参数:
  --output PATH     输出文件（默认 exports/outline.md）
""",
    "cases": """\
frostwords cases - 列出可用结局

读 tests/e2e_cases.json，显示每个结局的名称、脚本步数、附加状态断言。
这些脚本都由 tools/solve_e2e.py 用真实引擎求解并复现过。
""",
    "play": """\
frostwords play - 转发到 dse play

所有参数原样透传给引擎 CLI（含 --root 之后的部分）。
`--` 之后的内容不会被本工具解析。

示例:
  frostwords play --input 1,1,1,1 --banner
  frostwords play -- --entry core-open
""",
    "verify": """\
frostwords verify - 转发到 tools/verify.py（四层门禁）

参数原样透传，退出码原样返回。
  frostwords verify --fast
  frostwords verify --samples 100
""",
    "install-cli": """\
frostwords install-cli - 生成 .cmd 垫片并装到 PATH 目录

会写四份纯 ASCII + CRLF 的垫片：
  仓库根 frostwords.cmd / fwcli.cmd   （FW_ROOT=%~dp0，搬走也不失效）
  PATH 目录 frostwords.cmd / fwcli.cmd（FW_ROOT 为绝对路径）

目录优先级: --shim-dir → FW_BIN_DIR → <Python 前缀>\\Scripts
            → %LOCALAPPDATA%\\frostwords\\bin
本机 <Python 前缀>\\Scripts 已在 PATH，默认无需改环境变量。

参数:
  --shim-dir DIR    指定安装目录
  --dry-run          只打印将做的事，不写文件
  --add-to-path      目录不在 PATH 时写 HKCU\\Environment\\PATH
                     （用 winreg，不用会截断的 setx；新开终端才生效）

环境变量 FW_PYTHON 可覆盖垫片使用的 python.exe。
""",
    "uninstall-cli": """\
frostwords uninstall-cli - 卸载 PATH 垫片

只删除含 FW_CLI_SHIM 标记的文件；同名手工文件会跳过并列出。
仓库根的两份垫片保留。

参数:
  --shim-dir DIR    指定卸载目录
  --dry-run          只打印将做的事
""",
    "help": """\
frostwords help <命令> - 查看某命令的详细帮助
等价于 frostwords <命令> --help。
""",
}


class UsageError(Exception):
    """用法错误 → 退出码 2。"""


class EnvironmentError_(Exception):
    """环境缺失 → 退出码 6。"""


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise UsageError(message)


class Options:
    def __init__(self, as_json: bool = False, quiet: bool = False):
        self.as_json = as_json
        self.quiet = quiet


# ── stdio / 输出 ────────────────────────────────────────────────
def setup_stdio() -> None:
    """交互终端保持控制台代码页；重定向到文件/管道时用 UTF-8。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            if stream.isatty():
                stream.reconfigure(errors="replace")
            else:
                stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def out(msg: str) -> None:
    print(msg)


def info(msg: str, opts: Options) -> None:
    if not opts.quiet:
        print(f"[INFO] {msg}")


def ok(msg: str, opts: Options) -> None:
    if not opts.quiet:
        print(f"[OK] {msg}")


def err(msg: str) -> None:
    print(f"[ERR] {msg}", file=sys.stderr)


def strip_common(argv: list[str]) -> tuple[list[str], list[str]]:
    """抽出任意位置的全局选项；遇 `--` 停手，其后原样保留。"""
    common: list[str] = []
    rest: list[str] = []
    passthrough = False
    for tok in argv:
        if tok == "--" and not passthrough:
            passthrough = True
            rest.append(tok)
        elif not passthrough and tok in COMMON_FLAGS:
            common.append(tok)
        else:
            rest.append(tok)
    return common, rest


# ── 依赖（延迟导入，缺 dse-core 时才能报 6）────────────────────
def _core():
    try:
        import export_run
        return export_run
    except Exception as exc:
        raise EnvironmentError_(
            f"dse-core 或导出模块不可用：{exc}；请先 pip install dse-core"
        ) from exc


def _require_files(*paths: Path) -> None:
    for p in paths:
        if not p.exists():
            raise EnvironmentError_(f"缺少工程文件 {p}；请确认在仓库内运行")


# ── 命令实现 ───────────────────────────────────────────────────
def cmd_cases(args: list[str], opts: Options) -> dict:
    _require_files(ROOT / "tests" / "e2e_cases.json")
    core = _core()
    cases = core.load_cases()
    rows = [{"ending": k, "name": v.get("name", k),
             "steps": len(str(v.get("script", "")).split(",")),
             "expect": v.get("expect", [])}
            for k, v in sorted(cases.items())]
    return {"ok": True, "count": len(rows), "cases": rows}


def _parse_formats(raw: str) -> list[str]:
    if raw == "all":
        return list(FORMATS)
    items = [x.strip() for x in raw.split(",") if x.strip()]
    if not items:
        raise UsageError("--format 不能为空")
    bad = [x for x in items if x not in FORMATS]
    if bad:
        raise UsageError(f"未知格式 {bad}；可用 {', '.join(FORMATS)} / all")
    # 去重保序
    return list(dict.fromkeys(items))


def cmd_export_run(args: list[str], opts: Options) -> dict:
    ap = _Parser(prog="frostwords export-run", add_help=False)
    ap.add_argument("--ending")
    ap.add_argument("--script")
    ap.add_argument("--output")
    ap.add_argument("--format", default="md")
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--all-endings", action="store_true")
    ns = ap.parse_args(args)

    if ns.seed <= 0:
        raise UsageError("--seed 必须是正整数")
    if ns.script and ns.ending:
        raise UsageError("--script 与 --ending 互斥：二选一")
    if ns.all_endings and (ns.script or ns.output):
        raise UsageError("--all-endings 不接受 --script / --output")
    formats = _parse_formats(ns.format)

    core = _core()
    _require_files(ROOT / "dse.yml")
    cases = core.load_cases()

    if ns.all_endings:
        results = []
        for ending, case in sorted(cases.items()):
            r = core.export_run(case["script"].split(","), formats, None,
                                seed=ns.seed, label=case.get("name", ending))
            results.append({"ending": ending, "steps": r["steps"],
                            "final_scene": r["final_scene"], "files": r["files"]})
        return {"ok": True, "mode": "all-endings", "count": len(results),
                "formats": formats, "results": results}

    if ns.script:
        script = [x.strip() for x in ns.script.split(",") if x.strip()]
        label = "自定义脚本"
        if not script:
            raise UsageError("--script 解析后为空")
    else:
        ending = ns.ending or DEFAULT_ENDING
        if ending not in cases:
            near = difflib.get_close_matches(ending, list(cases), n=3, cutoff=0.4)
            hint = f"；是否想用 {', '.join(near)}" if near else ""
            raise UsageError(
                f"未知结局 '{ending}'{hint}；用 `frostwords cases` 查看全部")
        script = cases[ending]["script"].split(",")
        label = cases[ending].get("name", ending)

    output = Path(ns.output).expanduser() if ns.output else None
    result = core.export_run(script, formats, output, seed=ns.seed, label=label)
    return result


def cmd_export_outline(args: list[str], opts: Options) -> dict:
    ap = _Parser(prog="frostwords export-outline", add_help=False)
    ap.add_argument("--output")
    ns = ap.parse_args(args)
    core = _core()
    _require_files(ROOT / "dse.yml")
    path = Path(ns.output).expanduser() if ns.output else (ROOT / "exports" / "outline.md")
    path.parent.mkdir(parents=True, exist_ok=True)
    text = core.render_outline()
    path.write_text(text, encoding="utf-8")
    return {"ok": True, "file": str(path), "bytes": len(text.encode("utf-8")),
            "scenes": text.count("\n## `")}


def cmd_passthrough(args: list[str], opts: Options, base: list[str]) -> int:
    extra = args[1:] if args and args[0] == "--" else args
    try:
        return subprocess.call(base + list(extra))
    except FileNotFoundError as exc:
        raise EnvironmentError_(f"找不到可执行文件：{exc}") from exc


def cmd_install(args: list[str], opts: Options) -> dict:
    ap = _Parser(prog="frostwords install-cli", add_help=False)
    ap.add_argument("--shim-dir")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--add-to-path", action="store_true")
    ap.add_argument("--no-root", action="store_true",
                    help="不写仓库根垫片（测试/CI 用，避免污染工作树）")
    ns = ap.parse_args(args)
    import cli_shim
    d = Path(ns.shim_dir).expanduser() if ns.shim_dir else None
    return cli_shim.install(d, dry_run=ns.dry_run, modify_path=ns.add_to_path,
                            write_root=not ns.no_root)


def cmd_uninstall(args: list[str], opts: Options) -> dict:
    ap = _Parser(prog="frostwords uninstall-cli", add_help=False)
    ap.add_argument("--shim-dir")
    ap.add_argument("--dry-run", action="store_true")
    ns = ap.parse_args(args)
    import cli_shim
    d = Path(ns.shim_dir).expanduser() if ns.shim_dir else None
    return cli_shim.uninstall(d, dry_run=ns.dry_run)


def dispatch(cmd: str, args: list[str], opts: Options):
    if cmd == "cases":
        return cmd_cases(args, opts)
    if cmd == "export-run":
        return cmd_export_run(args, opts)
    if cmd == "export-outline":
        return cmd_export_outline(args, opts)
    if cmd == "install-cli":
        return cmd_install(args, opts)
    if cmd == "uninstall-cli":
        return cmd_uninstall(args, opts)
    if cmd == "play":
        return cmd_passthrough(
            args, opts,
            [sys.executable, "-m", "dse_core.cli", "play", "--root", str(ROOT)])
    if cmd == "verify":
        return cmd_passthrough(
            args, opts, [sys.executable, str(ROOT / "tools" / "verify.py")])
    raise UsageError(f"未知命令 '{cmd}'")


# ── 摘要输出 ───────────────────────────────────────────────────
def print_summary(cmd: str, result: dict, opts: Options) -> None:
    if cmd == "cases":
        for c in result["cases"]:
            out(f"  {c['ending']:<18} {c['steps']:>3} 步  {c['name']}")
        ok(f"共 {result['count']} 个可用结局", opts)
    elif cmd == "export-run":
        if result.get("mode") == "all-endings":
            for r in result["results"]:
                ok(f"{r['ending']:<18} {r['steps']:>3} 场景步 → {r['final_scene']}", opts)
            ok(f"已导出 {result['count']} 个结局，格式 {','.join(result['formats'])}", opts)
        else:
            for fmt, path in result["files"].items():
                ok(f"{fmt:<5} {path}", opts)
            ok(f"完整流程：{result['steps']} 场景步 / {result['scenes']} 不同场景 → "
               f"{result['final_scene']}", opts)
    elif cmd == "export-outline":
        ok(f"全场景大纲：{result['file']}（{result['bytes']:,} 字节）", opts)
    elif cmd == "install-cli":
        if result.get("dry_run"):
            for a in result["actions"]:
                info(a, opts)
            ok("dry-run 完成，未写入任何文件", opts)
        else:
            for p in result["files"]:
                ok(f"垫片 {p}", opts)
            if result["on_path"]:
                ok(f"目录已在 PATH：{result['shim_dir']}", opts)
            else:
                info(f"目录 {result['shim_dir']} 不在 PATH，三条修法：", opts)
                info("  1) 重新运行并加 --add-to-path（写 HKCU\\Environment\\PATH）", opts)
                info("  2) 用 --shim-dir 指定一个已在 PATH 的目录", opts)
                info("  3) 手动把该目录加入 PATH，然后新开终端", opts)
            info("现在可在任意目录使用 frostwords / fwcli（缩写避开 fw 别名冲突）", opts)
    elif cmd == "uninstall-cli":
        for p in result["removed"]:
            ok(f"移除 {p}", opts)
        for p in result["skipped"]:
            info(f"跳过（非本工具文件）{p}", opts)
        ok("卸载完成，仓库根垫片保留", opts)


# ── main ───────────────────────────────────────────────────────
def main(argv: list[str] | None = None) -> int:
    setup_stdio()
    common, rest = strip_common(list(argv if argv is not None else sys.argv[1:]))
    opts = Options(as_json="--json" in common,
                   quiet=("-q" in common or "--quiet" in common))

    if not rest:
        out(HELP)
        return 0
    head = rest[0]
    if head in ("-h", "--help"):
        out(HELP)
        return 0
    if head in ("--version", "-V"):
        out(f"frostwords {VERSION}")
        return 0
    if head == "help":
        out(HELP_DETAIL.get(rest[1], HELP) if len(rest) > 1 else HELP)
        return 0
    if head not in COMMANDS:
        near = difflib.get_close_matches(head, list(COMMANDS), n=3, cutoff=0.5)
        hint = f"；是否想用 {', '.join(near)}" if near else ""
        err(f"未知命令 '{head}'{hint}；用 `frostwords --help` 查看命令表")
        return 2
    args = rest[1:]
    if any(a in ("-h", "--help") for a in args):
        out(HELP_DETAIL[head])
        return 0

    try:
        result = dispatch(head, args, opts)
    except UsageError as exc:
        err(f"{exc}；用 `frostwords {head} --help` 查看用法")
        return 2
    except EnvironmentError_ as exc:
        err(str(exc))
        return 6
    except KeyboardInterrupt:
        err("已中断")
        return 130
    except Exception as exc:  # noqa: BLE001
        err(f"{type(exc).__name__}: {exc}")
        return 1

    if isinstance(result, int):
        return result          # 转发命令：原样返回子进程退出码
    if opts.as_json:
        out(json.dumps(result, ensure_ascii=False, default=str))
    else:
        print_summary(head, result, opts)
    return 0 if result.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
