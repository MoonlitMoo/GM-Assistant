import { application } from "./application"
import ContentPanelController from "./content_panel_controller"
import HelloController from "./hello_controller"
import TreeRefreshController from "./tree_refresh_controller"

application.register("content-panel", ContentPanelController)
application.register("hello", HelloController)
application.register("tree-refresh", TreeRefreshController)
