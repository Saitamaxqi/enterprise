import { cleanTerm } from "@mail/utils/common/format";

import { Component } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { imageUrl } from "@web/core/utils/urls";
import { DefaultCommandItem } from "@web/core/commands/command_palette";

const commandProviderRegistry = registry.category("command_provider");
const commandCategoryRegistry = registry.category("command_categories");

commandCategoryRegistry.add(
    "AI_AGENTS",
    { namespace: "@", name: _t("Agents") },
    { sequence: 30 },
);

export class AICommand extends Component {
    static template = "ai.AICommand";
    static props = {
        executeCommand: Function,
        name: String,
        subtitle: String,
        imgUrl: String,
        action: { type: Object, optional: true },
        searchValue: String,
        slots: Object,
    };

    setup() {
        super.setup();
        this.ui = useService("ui");
    }
}
export class AICommandPalette {
    constructor(env, options) {
        this.env = env;
        this.options = options;
        this.orm = env.services.orm;
        this.ui = env.services.ui;
        this.actions = env.services.action;
        this.commands = [];
        this.options = options;
        this.cleanedTerm = cleanTerm(this.options.searchValue);
        this.agents = []
    }

    async fetch() {
        this.agents = await this.orm.searchRead(
            "ai.agent",
            [["is_system_agent", "=", false]],
            ["id", "name", "subtitle", "partner_id"],
            {load: false}
        );
    }

    async buildResults(filtered) {
        this.agents
            .filter(
                (agent) =>
                    (cleanTerm(agent.name).includes(this.cleanedTerm) ||
                        (agent.subtitle && cleanTerm(agent.subtitle).includes(this.cleanedTerm))) &&
                    (!filtered || !filtered.has(agent)),
            )
            .slice(0, 5)
            .forEach((agent) => {
                this.commands.push({
                    Component: AICommand,
                    action: async () => {
                        const result = await this.orm.call("ai.agent", "open_agent_chat", [
                            agent.id,
                        ]);
                        if (result) {
                            this.actions.doAction(result);
                        }
                    },
                    name: agent.name,
                    props: {
                        imgUrl: imageUrl("ai.agent", agent.id, "image_128"),
                        subtitle: agent.subtitle ? agent.subtitle : "",
                    },
                    category: "AI_AGENTS",
                });
            });
    }
}

commandProviderRegistry.add("chat_with_agent", {
    namespace: "@",
    async provide(env, options) {
        const palette = new AICommandPalette(env, options);
        await palette.fetch();
        palette.buildResults();
        return palette.commands;
    },
});

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
        const agent = await orm.call("ai.agent", "get_ask_ai_agent", []);
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
