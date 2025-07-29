import { _t } from "@web/core/l10n/translation";
import { messageActionsRegistry } from "@mail/core/common/message_actions";

messageActionsRegistry.add("closeThread", {
    condition: (component) => component.env.closeThread && !component.env.isResolved(),
    icon: "fa fa-check",
    name: _t("Mark the discussion as resolved"),
    onSelected: (component) => component.env.closeThread(),
    sequence: 0,
});

messageActionsRegistry.add("openThread", {
    condition: (component) => component.env.openThread && component.env.isResolved(),
    icon: "fa fa-retweet",
    name: _t("Re-open the discussion"),
    onSelected: (component) => component.env.openThread(),
    sequence: 0,
});
