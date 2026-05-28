"""Qt application bootstrap - builds the engine, window and event loop."""

from __future__ import annotations

import sys

from ..config import AppConfig
from ..constants import APP_NAME, ORG_NAME
from ..engine import SmartFoldersEngine
from ..utils.logging import get_logger

log = get_logger(__name__)


def run_app(config: AppConfig | None = None, start_minimized: bool = False) -> int:
    """Launch the SmartFolders desktop application. Returns the exit code."""
    try:
        from PyQt6.QtWidgets import QApplication
    except Exception as exc:  # pragma: no cover
        log.error("PyQt6 is not installed: %s", exc)
        print(
            "PyQt6 is required to run the SmartFolders desktop UI.\n"
            "Install it with:  pip install PyQt6\n"
            "Or run the headless engine with:  python -m smartfolders --headless"
        )
        return 1

    config = config or AppConfig.load()

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(ORG_NAME)
    app.setQuitOnLastWindowClosed(False)  # we manage lifetime via the tray

    from .icons import app_icon

    app.setWindowIcon(app_icon(config.ui.accent_color))

    # First-run onboarding.
    if config.first_run:
        from .onboarding import OnboardingWizard

        wizard = OnboardingWizard(config)
        from PyQt6.QtWidgets import QWizard

        if wizard.exec() == QWizard.DialogCode.Accepted:
            config = wizard.apply()
        else:
            config.first_run = False
            config.save()

    engine = SmartFoldersEngine(config)

    from .main_window import MainWindow

    window = MainWindow(engine, config)

    if start_minimized or config.ui.start_minimized:
        window.hide()
    else:
        window.show()

    if config.autostart:
        engine.start()
        engine.scan_now()

    log.info("SmartFolders UI started")
    return app.exec()
