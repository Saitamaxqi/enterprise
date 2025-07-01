import { Thread } from "@mail/core/common/thread_model";
import { patch } from "@web/core/utils/patch";
import { rpc, RPCError } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";

patch(Thread.prototype, {
    async post(body, postData = {}, extraData = {}) {
        const message = await super.post(body, postData, extraData);
        const correspondentPersona = message?.thread?.correspondent?.persona;
        const aiMember = this.channel_member_ids?.find(
            (member) => member.partner_id?.im_status == "agent"
        );

        if (correspondentPersona && correspondentPersona.im_status === "agent") {
            try {
                if (aiMember) {
                    aiMember.isTyping = true;
                }
                await rpc("/ai/generate_response", {
                    mail_message_id: message.id,
                    agent_partner_id: correspondentPersona.id,
                    channel_id: this.id,
                });
            } catch (error) {
                if (error instanceof RPCError) {
                    await rpc("/ai/post_error_message", {
                        error_message:
                            error.data?.message ||
                            _t("An error occurred while generating the AI response."),
                        agent_partner_id: correspondentPersona.id,
                        channel_id: this.id,
                    });
                } else {
                    throw error;
                }
            } finally {
                if (aiMember) {
                    aiMember.isTyping = false;
                }
            }
        }
        return message;
    },
});
