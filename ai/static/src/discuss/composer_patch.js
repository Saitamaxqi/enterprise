import { Composer } from "@mail/core/common/composer";

import { patch } from "@web/core/utils/patch";

patch(Composer.prototype, {
    saveContent() {
        if (this.thread?.channel_type === "ai_composer") {
            return;  // no point in saving the content in an AI chat since chats are independent 
        }
        super.saveContent();
    },
    onFocusin(ev) {
        super.onFocusin();
        if (this.thread?.channel_type === "ai_composer") {
            ev.target.select();
        }
    }
});
