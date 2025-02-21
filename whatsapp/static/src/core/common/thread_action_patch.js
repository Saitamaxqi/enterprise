import { patch } from "@web/core/utils/patch";
import { threadActionsInternal } from "@mail/core/common/thread_actions";

patch(threadActionsInternal, {
    condition(component, id, action) {
        if (component.thread?.channel_type === "whatsapp") {
            if (id === "create-lead" && component.store.has_access_create_lead) {
                return true;
            }
            if (
                id === "create-ticket" &&
                component.store.has_access_create_ticket &&
                component.store.helpdesk_livechat_active
            ) {
                return true;
            }
        }
        return super.condition(component, id, action);
    },
});
