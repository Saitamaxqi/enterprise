import { Thread } from "@mail/core/common/thread";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    get showStartMessage() {
        return super.showStartMessage || (this.props.thread.channel_type === "ai_composer");
    },
    get startMessageSubtitle() {
        if (this.props.thread.channel_type === "ai_composer") {
            return _t("Hello, what can I help you with?");
        } else {
            return super.startMessageSubtitle;
        }
    },
});
