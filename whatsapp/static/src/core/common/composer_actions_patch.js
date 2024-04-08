import { composerActionsRegistry } from "@mail/core/common/composer_actions";
import { _t } from "@web/core/l10n/translation";

composerActionsRegistry.add("revive-whatsapp-conversation", {
    condition: (component) =>
        component.props.composer.thread?.channel_type === "whatsapp" && !component.state.active,
    icon: "fa fa-whatsapp",
    name: _t("Revive WhatsApp Conversation"),
    onClick: (component) => component.onclickWhatsAppChat(),
    sequenceQuick: 10,
});
