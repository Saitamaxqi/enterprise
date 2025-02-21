import { patch } from "@web/core/utils/patch";
import { threadActionsInternal } from "@mail/core/common/thread_actions";

patch(threadActionsInternal, {
    condition(component, id, action) {
        if (
            id === "create-ticket" &&
            component.store.helpdesk_livechat_active &&
            component.thread?.channel_type === "livechat" &&
            component.store.has_access_create_ticket
        ) {
            return true;
        }
        return super.condition(component, id, action);
    },
});
