import { Activity } from "@mail/core/common/activity_model";
import { patch } from "@web/core/utils/patch";

/** @type {import("models").Activity} */
const activityPatch = {
    requestSignature(onClose = () => {}, documentReference = false) {
        const additionalContext = {
            sign_directly_without_mail: false,
            default_activity_id: this.id,
        };
        if (documentReference) {
            additionalContext.default_reference_doc = documentReference;
            additionalContext.sign_from_activity = true;
            additionalContext.sign_from_record = true;
        }
        return this.store.env.services.action.doActionButton({
            type: "object",
            resModel: "sign.template",
            name:"open_sign_send_dialog",
            resIds: [],
            context: additionalContext,
        });
    },
};
patch(Activity.prototype, activityPatch);
