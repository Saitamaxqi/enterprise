import { patch } from "@web/core/utils/patch";
import { SearchBarMenu } from "@web/search/search_bar_menu/search_bar_menu";

patch(SearchBarMenu.prototype, {
    async onAskAIClick() {
        const orm = this.env.services.orm;
        const actions = this.env.services.action;
        const action = await orm.call("ai.agent", "action_ask_ai", [""]);
        if (action) {
            // Don't await so that the command palette can close immediately
            actions.doAction(action);
        }
    },
});
