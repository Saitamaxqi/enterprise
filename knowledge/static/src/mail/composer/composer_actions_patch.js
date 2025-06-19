import { composerActionsInternal } from "@mail/core/common/composer_actions";
import { patch } from "@web/core/utils/patch";

patch(composerActionsInternal, {
    condition(component, id, action) {
        // Always disable the send-message action for knowledge comment composer.
        // This is to avoid having two buttons for sending messages.
        if (id === "send-message" && component.env.inKnowledge) {
            return false;
        }
        return super.condition(component, id, action);
    },
});
