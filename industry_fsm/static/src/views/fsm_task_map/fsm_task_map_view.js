import { registry } from "@web/core/registry";
import { mapView } from "@web_map/map_view/map_view";
import { FsmTaskMapRenderer } from "./fsm_task_map_renderer";

export const fsmTaskMapView = {
    ...mapView,
    Renderer: FsmTaskMapRenderer,
};

registry.category("views").add("fsm_task_map", fsmTaskMapView);
