import { _t } from "@web/core/l10n/translation";
import { registerMessageAction } from "@mail/core/common/message_actions";

registerMessageAction("closeThread", {
    condition: (component) => component.env.closeThread && !component.env.isResolved(),
    icon: "fa fa-check",
    iconLarge: "fa fa-lg fa-check",
    name: _t("Mark the discussion as resolved"),
    onSelected: (component) => component.env.closeThread(),
    sequence: 0,
});

registerMessageAction("openThread", {
    condition: (component) => component.env.openThread && component.env.isResolved(),
    icon: "fa fa-retweet",
    iconLarge: "fa fa-lg fa-retweet",
    name: _t("Re-open the discussion"),
    onSelected: (component) => component.env.openThread(),
    sequence: 0,
});
