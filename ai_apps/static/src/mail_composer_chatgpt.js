import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

import { htmlJoin } from "@mail/utils/common/html";

import { Component, markup, onMounted, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class MailComposerChatGPT extends Component {
    static template = "mail.MailComposerChatGPT";
    static props = { ...standardFieldProps };

    setup() {
        this.store = useService("mail.store");
        this.orm = useService("orm");
        this.aiChatLauncher = useService("aiChatLauncher");
        onMounted(() => {
            this.store.aiInsertButtonTarget = this.props.record.id
        });
        onWillUnmount(() => {
            this.store.aiInsertButtonTarget = false
        });
    }

    async onOpenChatGPTPromptDialogBtnClick() {
        await this.aiChatLauncher.openAIChatFromContextV2({
            callerComponentName: 'composer_ai_button',
            originalRecordModel: this.props.record.data.model,
            originalRecordId: Number(this.props.record.data.res_ids.slice(1,-1)),
            originalRecordData: this.props.record.data,
            specialActionCallbacks: {
                insert: (content) => {
                    const root = document.createElement("div");
                    root.appendChild(content);
                    const { body } = this.props.record.data;
                    this.props.record.update({
                        body: htmlJoin(markup(root.innerHTML), body),
                    });
                },
            },
            aiChatSourceId: this.props.record.id,
            placeholderPrompt: _t("Write a followup answer"),
        });
    }
}

export const mailComposerChatGPT = {
    component: MailComposerChatGPT,
    fieldDependencies: [{ name: "body", type: "text" }],
};

registry.category("fields").add("mail_composer_chatgpt", mailComposerChatGPT);
