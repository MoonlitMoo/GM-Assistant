import { application } from "./application"
import AutoSubmitController from "./auto_submit_controller"
import ContentPanelController from "./content_panel_controller"
import HelloController from "./hello_controller"
import PlayerDisplayController from "./player_display_controller"
import TreeRefreshController from "./tree_refresh_controller"

application.register("auto-submit", AutoSubmitController)
application.register("content-panel", ContentPanelController)
application.register("hello", HelloController)
application.register("player-display", PlayerDisplayController)
application.register("tree-refresh", TreeRefreshController)
