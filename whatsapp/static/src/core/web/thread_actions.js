import { registerThreadAction } from "@mail/core/common/thread_actions";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

registerThreadAction("view-contact", {
    condition(component) {
        return (
            component.thread?.channel_type === "whatsapp" &&
            component.thread.whatsapp_partner_id &&
            !component.isDiscussSidebarChannelActions
        );
    },
    open(component) {
        if (component.ui.isSmall) {
            component.store?.ChatWindow.get({ thread: component.thread }).fold();
        } else {
            component.thread.openChatWindow({ focus: true });
        }
        component.action.doAction({
            type: "ir.actions.act_window",
            res_model: "res.partner",
            views: [[false, "form"]],
            res_id: component.thread.whatsapp_partner_id.id,
        });
    },
    icon: "fa fa-fw fa-address-book",
    iconLarge: "fa fa-fw fa-lg fa-address-book",
    name: _t("View Contact"),
    setup(component) {
        component.action = useService("action");
        component.ui = useService("ui");
    },
    sequenceGroup: (component) => (component.env.inDiscussApp ? 50 : 1),
});
