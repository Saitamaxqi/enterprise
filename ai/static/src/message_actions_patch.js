import { patch } from "@web/core/utils/patch";
import { messageActionsInternal } from "@mail/core/common/message_actions";

patch(messageActionsInternal, {
    condition(component, id, action) {
        if (component.message?.author?.im_status === "agent") {
            return false;
        }

        return super.condition(component, id, action);
    },
});
