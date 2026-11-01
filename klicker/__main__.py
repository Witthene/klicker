import argparse
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication


def main(argv=None):
    from . import macro

    payload = macro.read_embedded()  # a compiled macro .exe just plays and exits

    parser = argparse.ArgumentParser(prog="klicker")
    parser.add_argument("--screenshot", metavar="PNG", help="abre, captura a janela e fecha")
    parser.add_argument("--tab", type=int, default=0, help="aba a mostrar com --screenshot")
    parser.add_argument("--export-icon", metavar="FILE", help="salva o ícone do app (.ico/.png) e sai")
    args, _ = parser.parse_known_args(sys.argv[1:] if argv is None else argv)

    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv[:1])
    app.setApplicationName("Klicker")

    if payload is not None:
        from . import headless
        return headless.run(app, payload)

    from . import settings, theme
    from .icon import app_icon, save_ico
    from .window import MainWindow

    if args.export_icon:
        out = Path(args.export_icon)
        out.parent.mkdir(parents=True, exist_ok=True)
        if out.suffix.lower() == ".ico":
            return 0 if save_ico(out) else 1
        return 0 if app_icon().pixmap(256, 256).save(str(out)) else 1

    s = settings.load()
    theme.set_mode(s.theme)
    app.setStyleSheet(theme.stylesheet())
    window = MainWindow(s)
    window.show()

    if args.screenshot:
        window._go_to_tab(args.tab)
        QTimer.singleShot(1500, lambda: (window.save_screenshot(args.screenshot), window.close()))

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
