import { patch } from "@web/core/utils/patch";
import {
    threadActionsInternal,
    threadActionsRegistry,
} from "@mail/core/common/thread_actions";

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
    open(component) {
        super.open(component);
        if (component.thread?.correspondent?.persona.im_status === "agent") {
            component.store.env.services.orm.unlink("discuss.channel", [
                component.thread.id,
            ]);
        }
    },
});
