import { registry } from "@web/core/registry";
import { projectTaskMapView } from "@project_enterprise/views/project_task_map/project_task_map_view";
import { FsmMyTaskMapController } from "./fsm_my_task_map_controller";
import { FsmTaskMapRenderer } from "../fsm_task_map/fsm_task_map_renderer";

export const fsmMyTaskMapView = {
    ...projectTaskMapView,
    Controller: FsmMyTaskMapController,
    Renderer: FsmTaskMapRenderer,
};

registry.category("views").add("fsm_my_task_map", fsmMyTaskMapView);
