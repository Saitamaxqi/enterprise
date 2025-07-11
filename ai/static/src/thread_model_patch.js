import { Thread } from "@mail/core/common/thread_model";
import { patch } from "@web/core/utils/patch";
import { RPCError } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";

patch(Thread.prototype, {
    async post(body, postData = {}, extraData = {}) {
        const message = await super.post(body, postData, extraData);
        const correspondentPersona = message?.thread?.correspondent?.persona;
        const orm = this.store.env.services.orm;

        if (correspondentPersona) {
            const [agent] = await orm.searchRead(
                "ai.agent",
                [["partner_id", "=", correspondentPersona.id]],
                ["id"]
            );
            if (!agent) {
                return message;
            }
            try {
                await orm.call("ai.agent", "generate_response", [agent.id], {
                    mail_message_id: message.id,
                });
            } catch (error) {
                if (error instanceof RPCError) {
                    await orm.call("ai.agent", "post_error_message", [agent.id], {
                        error_message:
                            error.data?.message ||
                            _t("An error occurred while generating the AI response."),
                    });
                } else {
                    throw error;
                }
            }
        }
        return message;
    },
});
