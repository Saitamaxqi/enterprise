import { patch } from "@web/core/utils/patch";
import { ChatWindow } from "@mail/core/common/chat_window_model";
import { rpc } from "@web/core/network/rpc";

patch(ChatWindow.prototype, {
    async _onClose() {
        const thread = this.thread;
        if (thread?.livechat_with_ai_agent) {
            await rpc(
                "/ai/close_ai_chat", {channel_id: thread.id}
            );
        }
        await super._onClose();
    }
});
