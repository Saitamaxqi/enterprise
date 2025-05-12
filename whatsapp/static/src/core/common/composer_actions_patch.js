import {
    composerActionsInternal,
    composerActionsRegistry,
} from "@mail/core/common/composer_actions";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

composerActionsRegistry.add("revive-whatsapp-conversation", {
    condition: (component) =>
        component.props.composer.thread?.channel_type === "whatsapp" && !component.state.active,
    icon: "fa fa-whatsapp",
    name: _t("Revive WhatsApp Conversation"),
    onClick: (component) => component.onclickWhatsAppChat(),
    sequenceQuick: 10,
});

patch(composerActionsInternal, {
    condition(component, id, action) {
        if (
            ["upload-files", "voice-start"].includes(id) &&
            component.thread?.channel_type === "whatsapp" &&
            (component.props.composer.attachments.length > 0 || component.voiceRecorder?.recording)
        ) {
            return false;
        }
        return super.condition(component, id, action);
    },
});
