import { registry } from "@web/core/registry";

import { kanbanView } from "@web/views/kanban/kanban_view";
import { AccountReturnKanbanRenderer } from "./account_return_kanban_renderer";
import { AccountReturnKanbanModel } from "./account_return_kanban_model";

export const accountReturnKanbanView = {
    ...kanbanView,
    Renderer: AccountReturnKanbanRenderer,
    Model: AccountReturnKanbanModel
};

registry.category("views").add("account_return_kanban", accountReturnKanbanView);
