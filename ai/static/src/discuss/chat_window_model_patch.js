import { patch } from "@web/core/utils/patch";
import { ChatWindow } from "@mail/core/common/chat_window_model";

patch(ChatWindow.prototype, {
    computeCanShow() {
        if (this.store.aiInsertButtonTarget && this.store.discuss.isActive) {
            return this.thread?.channel_type === "ai_composer";
        }
        return super.computeCanShow();
    },
    async close(options) {
        const thread = this.thread;
        const orm = this.store.env.services.orm;
        if (["ai_composer", "ai_chat"].includes(thread?.channel_type)) {
            await orm.call("discuss.channel", "close_ai_chat", [thread.id]);
        }
        await super.close(options);
    },
});
