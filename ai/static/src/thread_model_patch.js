import { Thread } from "@mail/core/common/thread_model";
import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    async post(body, postData = {}, extraData = {}) {
        const message = await super.post(body, postData, extraData);
        const correspondentPersona = message?.thread?.correspondent?.persona;
        const orm = this.store.env.services.orm;

        if (correspondentPersona) {
            const agents = await orm.searchRead(
                "ai.agent",
                [["partner_id", "=", correspondentPersona.id]],
                ["id"]
            );
            orm.call("ai.agent", "generate_response", [agents.map(({ id }) => id)], {
                prompt: message.body,
            });
        }
    },
});
