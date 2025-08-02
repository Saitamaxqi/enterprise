import { patch } from "@web/core/utils/patch";
import { Thread } from "@mail/core/common/thread_model";

patch(Thread.prototype, {
    async notifyMessageToUser(message) {
        // Prevent showing a notification when the livechat channel opened from ai_livechat snippet is closed
        if (this.channel_type === 'livechat' && message.thread.livechat_end_dt && this.livechat_with_ai_agent){
            return;
        }
        super.notifyMessageToUser(message);
    }
});

