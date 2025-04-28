import { patch } from "@web/core/utils/patch";
import { threadActionsInternal, threadActionsRegistry } from "@mail/core/common/thread_actions";

patch(threadActionsInternal, {
    condition(component, id, action) {
        const filters = ["close", "fold-chat-window", "expand-discuss"];

        if (
            component.thread?.correspondent?.persona.im_status === "agent" &&
            !filters.includes(id)
        ) {
            return false;
        }
        return super.condition(component, id, action);
    },
});

patch(threadActionsRegistry.get("close"), {
    async open(component) {
        super.open(component);

        const correspondentPersona = component.thread?.correspondent?.persona;
        if (correspondentPersona?.im_status === "agent") {
            const orm = component.store.env.services.orm;
            const agents = await orm.searchRead(
                "ai.agent",
                [["partner_id", "=", correspondentPersona.id]],
                ["id"]
            );
            orm.call("ai.agent", "close_chat", [agents.map(({ id }) => id)], {
                channel_id: component.thread?.id,
            });
        }
    },
});
