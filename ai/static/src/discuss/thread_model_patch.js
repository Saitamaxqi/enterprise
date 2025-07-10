import { Thread } from "@mail/core/common/thread_model";

import { patch } from "@web/core/utils/patch";
import { rpc } from "@web/core/network/rpc";
import { url } from "@web/core/utils/urls";

patch(Thread.prototype, {
    async generate(prompt, channel_id) {
        await rpc(
            "/ai/generate_w_composer",
            {
                prompt,
                channel_id,
            },
            { silent: true }
        );
    },
    async post() {
        const message = await super.post(...arguments);
        if (this.channel_type === "ai_composer") {
            await this.generate(message.body, this.id);
        }
        return message;
    },
    get avatarUrl() {
        if (this.channel_type === "ai_composer") {
            return url("/ai/static/description/icon.png");
        }
        if (this.channel_type === "ai_chat" && this.correspondent) {
            return this.correspondent.persona.avatarUrl;
        }

        return super.avatarUrl;
    },
});
