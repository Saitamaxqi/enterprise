import { patch } from "@web/core/utils/patch";
import { threadActionsRegistry, threadActionsInternal } from "@mail/core/common/thread_actions";

patch(threadActionsRegistry.get("close"), {
    async open(component) {
        const correspondentPersona = component.thread?.correspondent?.persona;
        const orm = component.store.env.services.orm;
        if (correspondentPersona?.im_status === "agent") {
            const agents = await orm.searchRead(
                "ai.agent",
                [["partner_id", "=", correspondentPersona.id]],
                ["id"]
            );
            orm.call("ai.agent", "close_chat", [agents.map(({ id }) => id)], {
                channel_id: component.thread?.id,
            });
        } else if (component.thread?.channel_type === "ai_composer") {
            orm.call("discuss.channel", "close_ai_chat", [component.thread.id]);
        }
        await super.open(component);
    },
});

patch(threadActionsInternal, {
    condition(component, id, action) {
        const requiredActions = ["close", "fold-chat-window", "expand-discuss"];
        if (
            (
                component.thread?.channel_type === "ai_composer" ||
                component.thread?.correspondent?.persona.im_status === "agent"
            ) && !requiredActions.includes(id)
        ) {
            return false;
        }
        return super.condition(component, id, action);
    }
})
