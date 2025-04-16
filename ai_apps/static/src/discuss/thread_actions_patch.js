import { patch } from "@web/core/utils/patch";
import { threadActionsRegistry, threadActionsInternal } from "@mail/core/common/thread_actions";

patch(threadActionsRegistry.get("close"), {
    open(component) {
        super.open(component);
        if (component.thread?.channel_type === "ai_composer") {
            component.store.env.services.orm.unlink("discuss.channel", [component.thread.id]);
        }
    },
});

patch(threadActionsInternal, {
    condition(component, id, action) {
        const requiredActions = ["close", "fold-chat-window", "expand-discuss"];
        if (
            component.thread?.channel_type === 'ai_composer' && 
            !requiredActions.includes(id)
        ) {
            return false;
        }
        return super.condition(component, id, action);
    }
})
