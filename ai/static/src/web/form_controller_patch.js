import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";
import { useService } from "@web/core/utils/hooks";
import { onWillUnmount } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";


patch(FormController.prototype, {
    setup() {
        super.setup();
        this.aiChatLauncher = useService("aiChatLauncher");
        this.actionService = useService("action");
        onWillUnmount(() => {
            if (this.store?.aiInsertButtonTarget) {
                this.store.aiInsertButtonTarget = false
            }
        });
    },
    async onClickLaunchAIChat() {
        // Force save the record so we can fetch chatter messages from the back-end
        const saved = await this.model.root.save();
        if (!saved) {
            return;
        }
        let composerAction = {
            type: "ir.actions.act_window",
            view_mode: "form",
            res_model: "mail.compose.message",
            views: [[false, "form"]],
            target: "new",
            view_id: false,
            context: {
                default_model: this.model.root.resModel,
                default_res_ids: [this.model.root.resId],
                clicked_on_full_composer: true,
            },
        }
        const thread = await this.mailStore.Thread.get({
            model: this.model.root.resModel,
            id: this.model.root.resId,
        });
        await this.aiChatLauncher.launchAIChat({
            callerComponentName: 'chatter_ai_button',
            recordModel: this.model.root.resModel,
            recordId: this.model.root.resId,
            originalRecordData: this.model.root.data,
            originalRecordFields: this.model.root.fields,
            aiChatSourceId: this.model.root.resId,
            aiSpecialActions: {
                sendMessage: (content) => {
                    composerAction['name'] = _t("Send Message");
                    composerAction['context']['default_subtype_xmlid'] = "mail.mt_comment";
                    composerAction['context']['default_body'] = content;
                    this.actionService.doAction(composerAction, {
                        onClose: () => thread?.fetchNewMessages(),
                    });
                },
                logNote: (content) => {
                    composerAction['name'] = _t("Log Note");
                    composerAction['context']['default_subtype_xmlid'] = "mail.mt_note";
                    composerAction['context']['default_body'] = content;
                    this.actionService.doAction(composerAction, {
                        onClose: () => thread?.fetchNewMessages(),
                    });
                }
            },
            channelTitle: this.model.root.data.display_name,
        });
    },
    get show_AI_control_panel_button() {
        return this.model.root.fields?.message_ids;  // should only be available if model has chatter
    },
});
