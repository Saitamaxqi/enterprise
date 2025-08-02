import { rpc } from "@web/core/network/rpc";
import { patch } from "@web/core/utils/patch";
import { ChatWindow } from "@mail/core/common/chat_window_model";

patch(ChatWindow.prototype, {
    computeCanShow() {
        if (this.store.aiInsertButtonTarget && this.store.discuss.isActive) {
            return this.thread?.channel_type === "ai_composer";
        }
        return super.computeCanShow();
    },
    async _onClose() {
        const thread = this.thread;
        if (["ai_composer", "ai_chat"].includes(thread?.channel_type)) {
            await rpc(
                "/ai/close_ai_chat", {channel_id: thread.id}
            );
        }
        await super._onClose();
    },
});
