import sys

from dmt.app import main
from dmt.ui.player_window.start_player import main as player_main

if __name__ == "__main__":
    if "--player" in sys.argv:
        player_main()
    main()
