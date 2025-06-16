import { rpc } from "@web/core/network/rpc";
import { patch } from "@web/core/utils/patch";
import { ChatWindow } from "@mail/core/common/chat_window_model";

patch(ChatWindow.prototype, {
    computeCanShow() {
        if (this.store.aiInsertButtonTarget && this.store.discuss.isActive) {
            return this.thread?.channel_type === "ai_chat";
        }
        return super.computeCanShow();
    },
    async _onClose() {
        const thread = this.thread;
        if (thread?.channel_type === "ai_chat") {
            await rpc(
                "/ai/close_ai_chat", {channel_id: thread.id}
            );
        }
        await super._onClose();
    },
});
