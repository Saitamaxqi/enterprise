import { patch } from "@web/core/utils/patch";
import { composerActionsInternal } from "@mail/core/common/composer_actions";

patch(composerActionsInternal, {
    condition(component, id, action) {
        const requiredActions = ["send-message"];
        if (
            component.thread?.correspondent?.persona.im_status === "agent" && !requiredActions.includes(id)
        ) {
            return false;
        }
        return super.condition(component, id, action);
    },
});
