"""《梦层》独立启动器入口。

打包成 exe 后，双击运行时：
- 工作目录固定为 exe 自身所在目录，存档与相对资源都落在 exe 旁边；
- 默认把自动存档写到 ``<exe 目录>/save``，避免污染用户目录或桌面；
- 崩溃与诊断报告统一写进 ``<exe 目录>/crash_reports/``（2026-09-22 起），
  主目录只留游戏本体、存档与说明书；并保留窗口（回车关闭），
  避免控制台程序「闪退」后无从诊断。
其余行为完全委托给 ``run_demo``（即 ``python run_demo.py``）。
"""
from __future__ import annotations

import os
import sys
import threading
import time
import traceback
from pathlib import Path

# 正常游玩时进程会一直存活；若从启动到退出不足这个秒数，几乎必定是异常
# 退出（Textual 没能进入应用模式、驱动初始化失败等），此时留下日志。
_FAST_EXIT_SECONDS = 3.0
# 只有「几乎瞬间」退出才保留窗口：正常按 q 退出也可能在 1~3 秒内发生，
# 那种情况只留日志、不拦着玩家关窗口。
_INSTANT_EXIT_SECONDS = 1.5
# 崩溃报告目录名（exe 同级的子目录）。全英文：报告文件、目录名、日志内容
# 一律避免非 ASCII 路径——玩家转发、命令行查看、跨机器解压都不会踩编码问题。
_CRASH_DIR_NAME = "crash_reports"
# 最多保留这么多份报告，超出的按时间从旧到新删除（长期游玩不至于膨胀）。
_MAX_REPORTS = 10

# 本次运行的报告文件：延迟到「真的要写」时才定名（见 _log_path）。
_session_log: Path | None = None
_log_header_pending = True


def _crash_directory() -> Path:
    return _exe_directory() / _CRASH_DIR_NAME


def _log_path() -> Path:
    """本次运行的报告文件路径（文件名带启动时刻，各次运行互不覆盖）。

    同一秒内重复启动（脚本连点、自动化跑测）也要各留一份，故再加一个
    递增后缀。
    """
    global _session_log
    if _session_log is None:
        stamp = time.strftime("%Y%m%d_%H%M%S")
        candidate = _crash_directory() / f"crash_{stamp}.log"
        index = 2
        while candidate.exists():
            candidate = _crash_directory() / f"crash_{stamp}_{index}.log"
            index += 1
        _session_log = candidate
    return _session_log


def _prepare_log_directory() -> None:
    """启动时准备报告目录：确保存在，并清掉过老的历史报告。

    旧实现是「每次启动清空 crash.log」——玩家重启一次就把上一份证据删掉，
    这恰好和「留证据用来反馈」的用途相反。现在改为**按次成文**：同一进程内的
    多条诊断追加进同一个文件，不同次运行各留一份，只保留最近 _MAX_REPORTS 份。
    """
    try:
        directory = _crash_directory()
        directory.mkdir(parents=True, exist_ok=True)
        for stale in sorted(directory.glob("crash_*.log"))[:-_MAX_REPORTS]:
            try:
                stale.unlink()
            except OSError:
                pass
    except OSError:
        pass


def _write_log(detail: str) -> Path | None:
    """把诊断信息追加进本次运行的报告文件（写失败不影响退出流程）。

    用追加而不是覆盖：线程崩溃与主线程退出可能先后各写一条，覆盖会丢掉
    真正的原因。首条之前补一段环境信息（时间/exe 位置/Python 版本），
    省得玩家反馈时还要另外说明。
    """
    global _log_header_pending
    try:
        path = _log_path()
        path.parent.mkdir(parents=True, exist_ok=True)  # 目录被玩家删掉时补建
        with path.open("a", encoding="utf-8") as stream:
            if _log_header_pending:
                _log_header_pending = False
                stream.write(
                    f"《梦层》诊断报告\n时间：{time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"位置：{_exe_directory()}\nPython：{sys.version.split()[0]}\n"
                    + "-" * 40 + "\n"
                )
            stream.write(detail)
            if not detail.endswith("\n"):
                stream.write("\n")
        return path
    except OSError:
        return None


def _install_thread_hook() -> None:
    """后台线程崩溃兜底。

    Textual 的原生鼠标监听跑在独立线程里；线程里的未捕获异常不会走
    sys.excepthook，过去会**完全静默**（进程随后退出 = 只剩一闪）。
    这里把它也落到报告文件。
    """

    def _hook(args) -> None:
        detail = "".join(
            traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback)
        )
        _write_log(f"[线程 {getattr(args.thread, 'name', '?')} 崩溃]\n{detail}")
        print(detail, file=sys.stderr)

    threading.excepthook = _hook


def _hold_window(reason: str) -> None:
    """保留控制台窗口，避免「一闪而过」后无从诊断。

    非交互环境（输出被重定向/无 stdin）下 input 会抛异常，静默跳过。
    """
    try:
        print(reason, file=sys.stderr)
        input("按回车键关闭……")
    except (EOFError, OSError, RuntimeError):
        pass


def _run_guarded() -> int:
    """带闪退防护的入口。

    覆盖三种「一打开就闪退」的静默路径：
    1. 未捕获异常 → 落盘 + 保留窗口；
    2. SystemExit（Textual 内部出错后就是这样退出的，旧版会**完全静默**）
       → 非 0 退出码或过快退出时落盘提示；
    3. 后台线程崩溃 → 由 threading.excepthook 落盘。
    """
    if '--prepare-terminal' in sys.argv:
        from dream_demo.terminal_launch import prefer_wezterm
        return 0 if prefer_wezterm(sys.argv,_exe_directory()) else 2
    # Frozen Python ignores PYTHONIOENCODING. Redirected smoke/log output still
    # needs the full Unicode tile set, including glyphs absent from Windows GBK.
    for stream in (sys.stdout, sys.stderr):
        if not stream.isatty() and hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    from dream_demo.terminal_launch import ATTACHED_FLAG, handoff
    if "--serif-terminal" in sys.argv and ATTACHED_FLAG not in sys.argv and "--smoke" not in sys.argv:
        command = ([sys.executable] if getattr(sys, "frozen", False)
                   else [sys.executable, str(Path(__file__).resolve())])
        if handoff([*command, ATTACHED_FLAG, *sys.argv[1:]], _exe_directory()):
            return 0  # 正常交接，不触发“过快退出”的日志与窗口保留。
    _install_thread_hook()
    _prepare_log_directory()
    started = time.monotonic()
    try:
        handed_off=main()
    except SystemExit as exit_request:
        code = int(exit_request.code or 0)
        elapsed = time.monotonic() - started
        if code != 0 or elapsed < _FAST_EXIT_SECONDS:
            detail = (
                f"程序在 {elapsed:.1f} 秒内退出（退出码 {code}）。\n"
                "这通常是终端没能进入应用模式（如被旧版 conhost/输入法/安全软件拦截）。\n"
            )
            path = _write_log(detail)
            if code != 0 or elapsed < _INSTANT_EXIT_SECONDS:
                _hold_window(detail + (f"\n诊断已写入：{path}" if path else ""))
        return code
    except BaseException:
        # BaseException：连 KeyboardInterrupt / MemoryError 也一并记录，
        # 保证任何情况下都不出现「无日志的一闪」。
        detail = traceback.format_exc()
        path = _write_log(detail)
        print(detail, file=sys.stderr)
        if path:
            print(f"回溯已写入：{path}", file=sys.stderr)
        _hold_window("游戏异常结束。")
        return 1
    if handed_off is True:
        return 0
    elapsed = time.monotonic() - started
    if "--smoke" in sys.argv:
        return 0  # 单帧检查本来就应快速结束，不属于交互窗口闪退。
    if elapsed < _FAST_EXIT_SECONDS:
        # 正常返回但极快退出：同样可疑，留痕；几乎瞬间的才拦窗口。
        detail = f"程序在 {elapsed:.1f} 秒内正常返回（未抛异常）。\n"
        path = _write_log(detail)
        if elapsed < _INSTANT_EXIT_SECONDS:
            _hold_window(detail + (f"\n诊断已写入：{path}" if path else ""))
    return 0


def _exe_directory() -> Path:
    """返回真正 exe 所在的目录（onefile 下 sys.argv[0] 指向发布出的 exe）。"""
    if "--game-directory" in sys.argv:
        index = sys.argv.index("--game-directory")
        if index + 1 < len(sys.argv):
            return Path(sys.argv[index + 1]).resolve()
    try:
        candidate = Path(sys.argv[0]).resolve()
    except (OSError, ValueError):
        candidate = Path(sys.executable)
    if candidate.is_file():
        return candidate.parent
    return Path(sys.executable).parent


def main() -> bool | None:
    exe_dir = _exe_directory()
    # 固定 cwd，保证相对路径（如存档、潜在资源）都相对 exe 目录解析。
    os.chdir(exe_dir)
    # Windows Terminal 专用 profile 自愈（docs §5）：每次运行都把 Fragments
    # 的 commandline/字体/氛围刷新到当前 exe——否则换包/挪目录后 WT 里点的
    # 还是旧 profile（实测踩过：profile 一直指旧 runtime，用户看到旧版）。
    # 静默失败即可（无 LOCALAPPDATA/权限受限的机器跳过，游戏照常跑）。
    try:
        if "--smoke" not in sys.argv and getattr(sys, "frozen", False):
            # 只在打包态刷新：sys.executable 就是实际被双击的 exe（含改名副本）。
            from dream_demo.terminal_launch import ATTACHED_FLAG, install_profile
            install_profile([str(Path(sys.executable).resolve()), ATTACHED_FLAG], exe_dir)
    except Exception:
        pass
    # 默认存档目录放在 exe 旁边；若用户额外传了 --save-dir 则尊重用户的。
    if "--save-dir" not in sys.argv and "-save-dir" not in sys.argv:
        sys.argv = [sys.argv[0], "--save-dir", str(exe_dir / "save"), *sys.argv[1:]]
    from run_demo import main as run_demo_main

    return run_demo_main()


if __name__ == "__main__":
    sys.exit(_run_guarded())
