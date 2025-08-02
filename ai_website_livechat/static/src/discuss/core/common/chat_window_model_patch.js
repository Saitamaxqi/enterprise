import { ChatWindow } from "@mail/core/common/chat_window_model";
import { patch } from "@web/core/utils/patch";

patch(ChatWindow.prototype, {
    _onClose(options = {}) {
        const channelId = this.thread?.id
        super._onClose();
        if(channelId){
            this.store.env.bus.trigger('CHATWINDOW_CLOSED', { channelId: channelId });
        }
    },
});
