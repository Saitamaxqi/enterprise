import { threadActionsRegistry } from "@mail/core/common/thread_actions";
import "@mail/discuss/call/common/thread_actions";

import { LivechatCommandDialog } from "@im_livechat/core/common/livechat_command_dialog";

import { useComponent } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { usePopover } from "@web/core/popover/popover_hook";

threadActionsRegistry.add("create-ticket", {
    close: (component, action) => action.popover?.close(),
    component: LivechatCommandDialog,
    componentProps: (action) => ({
        close: () => action.close(),
        commandName: "ticket",
        placeholderText: _t("e.g. Product arrived damaged"),
        title: _t("Create Ticket"),
        icon: "fa fa-life-ring",
    }),
    condition: (component) => false,
    panelOuterClass: "bg-100",
    icon: "fa fa-life-ring fa-fw",
    iconLarge: "fa-lg fa fa-life-ring fa-fw",
    name: _t("Create Ticket"),
    sequence: 15,
    sequenceGroup: 25,
    setup(action) {
        const component = useComponent();
        if (!component.env.inChatWindow) {
            action.popover = usePopover(LivechatCommandDialog, {
                onClose: () => action.close(),
                popoverClass: action.panelOuterClass,
            });
        }
    },
    toggle: true,
    open(component, action) {
        action.popover?.open(component.root.el.querySelector(`[name="${action.id}"]`), {
            thread: component.thread,
            ...action.componentProps,
        });
    },
});
