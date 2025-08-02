import { Thread } from "@mail/core/common/thread_model";
import { patch } from "@web/core/utils/patch";
import { rpc, RPCError } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";

patch(Thread.prototype, {
    async post(body, postData = {}, extraData = {}) {
        const message = await super.post(body, postData, extraData);
        const correspondentPersona = message?.thread?.correspondent?.persona;

        if (correspondentPersona && correspondentPersona.im_status === "agent") {
            try {
                await rpc(
                    "/ai/generate_response",
                    {
                        mail_message_id: message.id,
                        agent_partner_id: correspondentPersona.id,
                        channel_id: this.id,
                    }
                );
            } catch (error) {
                if (error instanceof RPCError) {
                    await rpc(
                        "/ai/post_error_message",
                        {
                            error_message:
                                error.data?.message ||
                                _t("An error occurred while generating the AI response."),
                            agent_partner_id: correspondentPersona.id,
                            channel_id: this.id,
                        }
                    );
                } else {
                    throw error;
                }
            }
        }
        return message;
    },
});
