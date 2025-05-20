import { registry } from "@web/core/registry";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { AccountReturnKanbanController } from "./account_return_kanban_controller";
import { AccountReturnKanbanRenderer } from "./account_return_kanban_renderer";
import { AccountReturnKanbanModel } from "./account_return_kanban_model";

export const accountReturnKanbanView = {
    ...kanbanView,
    Controller: AccountReturnKanbanController,
    Renderer: AccountReturnKanbanRenderer,
    Model: AccountReturnKanbanModel
};

registry.category("views").add("account_return_kanban", accountReturnKanbanView);
