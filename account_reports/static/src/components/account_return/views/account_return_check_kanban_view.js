import { registry } from "@web/core/registry";

import { kanbanView } from "@web/views/kanban/kanban_view";
import { AccountReturnCheckKanbanRenderer } from "./account_return_check_kanban_renderer";

export const accountReturnCheckKanbanView = {
    ...kanbanView,
    Renderer: AccountReturnCheckKanbanRenderer,
};

registry.category("views").add("account_return_check_kanban", accountReturnCheckKanbanView);
