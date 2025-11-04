import sys

from PySide6.QtWidgets import QApplication

from dmt.core import PlayerDisplayState
from dmt.core.config import APP, ORG
from dmt.core.platform_helpers import set_app_identity

from dmt.ui.player_window import PlayerWindow, PlayerClient


def main():
    args = sys.argv[1:]
    if len(args) >= 2 and args[0] == "--socket":
        name = args[1]
    else:
        print("player_process: missing --socket <name>", file=sys.stderr)
        sys.exit(2)

    app_name = f"{APP}-player"
    app = QApplication(sys.argv)
    QApplication.setOrganizationName(ORG)
    QApplication.setApplicationName(app_name)
    set_app_identity("GMAssistant.Player", app_name)

    # Create objects
    dp = PlayerDisplayState(is_receiver=True)
    win = PlayerWindow(display_state=dp)
    client = PlayerClient(name, win)
    dp.socket = client

    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
