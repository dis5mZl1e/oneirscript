from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rich.console import Console

from dream_demo.app import DreamApp, create_session, render_map
# ⚠️ 这一行必须留在 dream_demo.app 之后：install_gc_tuning 冻的是「此刻已存在的
# 对象」，若它先跑，整条依赖树会被当成新对象重新纳入回收，等于白冻。
from dream_demo.perf import install_gc_tuning


def main() -> bool | None:
    install_gc_tuning()
    parser = argparse.ArgumentParser(description="Oneirscript vertical slice")
    parser.add_argument("--smoke", action="store_true", help="render one frame and save without entering the UI")
    parser.add_argument("--image-smoke", action="store_true", help="verify bundled image map and glyphs (use with --smoke)")
    parser.add_argument("--fx-smoke", action="store_true", help="verify bundled offscreen effects (use with --smoke)")
    parser.add_argument("--save-dir", default="save", help="directory for the automatic save")
    parser.add_argument("--serif-terminal", action="store_true", help="launch in the game's serif Windows Terminal profile")
    parser.add_argument("--terminal-attached", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument('--wezterm-attached',action='store_true',help=argparse.SUPPRESS)
    parser.add_argument('--compat-terminal',action='store_true',help='use the current terminal without automatic handoff')
    parser.add_argument('--unified-font',action='store_true',help=argparse.SUPPRESS)
    parser.add_argument("--game-directory", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.unified_font:
        from dream_demo.terminal_launch import set_unified_font
        set_unified_font(True)
    if args.image_smoke and not args.smoke:
        parser.error("--image-smoke requires --smoke")
    if args.fx_smoke:
        if not args.smoke:
            parser.error('--fx-smoke requires --smoke')
        import json
        from dream_demo.ui.fx_diagnostics import smoke_fx
        print(json.dumps(smoke_fx(), ensure_ascii=True, sort_keys=True))
    if args.serif_terminal and not args.terminal_attached and not args.smoke:
        from dream_demo.terminal_launch import ATTACHED_FLAG, handoff
        if handoff([sys.executable, str(Path(__file__).resolve()), ATTACHED_FLAG,
                    "--save-dir", str(Path(args.save_dir).resolve())], Path(__file__).resolve().parent):
            return True
    if not args.smoke and not args.terminal_attached:
        from dream_demo.terminal_launch import prefer_wezterm
        directory=(Path(args.game_directory).resolve() if args.game_directory else
                   Path(sys.executable).resolve().parent if getattr(sys,'frozen',False) else
                   Path(__file__).resolve().parent)
        if prefer_wezterm(sys.argv,directory):
            return True
    session = create_session(Path(args.save_dir))
    if args.smoke:
        session.start()
        if args.image_smoke:
            import json
            from dream_demo.ui.image_preview import render_preview_png
            from dream_demo.ui.map_presentation import font_sources, glyph_mask
            image_path=render_preview_png(session.state,Path(args.save_dir)/'image-map-smoke.png')
            count=0
            for path,codes in font_sources():
                if 'SongReading' not in path:
                    for code in codes:
                        if glyph_mask(chr(code),24,24) is not None:
                            count+=1
            print(json.dumps({'image_smoke':True,'glyphs':count,'png_bytes':image_path.stat().st_size,
                              'frozen':bool(getattr(sys,'frozen',False))},sort_keys=True))
        console = Console(legacy_windows=False)
        console.print(render_map(session.state))
        console.print(f"梦痕已保存：{session.manager.primary}")
        return
    import os
    app=DreamApp(session)
    app.terminal_compatibility_notice=(args.compat_terminal or not os.environ.get('WEZTERM_PANE'))
    app.run()


if __name__ == "__main__":
    main()
