import { application } from "./application"
import ContentPanelController from "./content_panel_controller"
import HelloController from "./hello_controller"
import PlayerDisplayController from "./player_display_controller"
import TreeRefreshController from "./tree_refresh_controller"

application.register("content-panel", ContentPanelController)
application.register("hello", HelloController)
application.register("player-display", PlayerDisplayController)
application.register("tree-refresh", TreeRefreshController)
