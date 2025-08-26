import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { imageUrl } from "@web/core/utils/urls";
import { DefaultCommandItem } from "@web/core/commands/command_palette";

const commandProviderRegistry = registry.category("command_provider");

class AskAICommand extends Component {
    static template = "ai.AskAICommand";
    static props = {
        imgUrl: String,
        ...DefaultCommandItem.props,
    };
}

commandProviderRegistry.add("ask_ai", {
    namespace: "/",
    async provide(env, options) {
        const orm = env.services.orm;
        const actions = env.services.action;
        const agent = await orm.cache().call("ai.agent", "get_ask_ai_agent", []);
        return [
            {
                action: async () => {
                    const action = await orm.call("ai.agent", "action_ask_ai", [
                        options.searchValue,
                    ]);
                    if (action) {
                        // Don't await so that the command palette can close immediately
                        actions.doAction(action);
                    }
                },
                Component: AskAICommand,
                props: {
                    imgUrl: imageUrl("ai.agent", agent.id, "image_128"),
                },
                name: _t("Ask AI"),
            },
        ];
    },
});
