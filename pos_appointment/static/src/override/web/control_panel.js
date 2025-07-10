import { ControlPanel } from "@web/search/control_panel/control_panel";
import { patch } from "@web/core/utils/patch";

patch(ControlPanel.prototype, {
    switchView(viewType, newWindow) {
        const searchModel = this.env.searchModel;
        const kanbanDateFilter = Object.values(searchModel.searchItems).find(
            (sm) => sm.name === "kanban_date_filter"
        );
        if (
            kanbanDateFilter &&
            searchModel.query.some((sm) => sm.searchItemId === kanbanDateFilter.id)
        ) {
            searchModel.toggleSearchItem(kanbanDateFilter.id);
        }
        super.switchView(...arguments);
    },
});
