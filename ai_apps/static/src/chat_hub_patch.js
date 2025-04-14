import { patch } from "@web/core/utils/patch";
import { ChatHub } from "@mail/core/common/chat_hub";

patch(ChatHub.prototype, {
    displayChatHub(cw) {
        if (this.store.aiInsertButtonTarget && this.store.discuss.isActive) {
            return cw.thread?.channel_type === "ai_composer";
        }
        return super.displayChatHub(cw);
    },
});
