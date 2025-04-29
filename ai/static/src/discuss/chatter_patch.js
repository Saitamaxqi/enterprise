import { Chatter } from "@mail/chatter/web_portal/chatter";
import { convertBrToLineBreak } from "@mail/utils/common/format";

import { onWillUnmount } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";


/**
 * @type {import("@mail/chatter/web_portal/chatter").Chatter }
 * @typedef {Object} Props
 * @property {function} [close]
 */
patch(Chatter.prototype, {
    setup() {
        super.setup();
        this.aiChatLauncher = useService("aiChatLauncher");
        onWillUnmount(() => {
            this.store.aiInsertButtonTarget = false
        });
    },
    async onClickAIChatterButton() {
        // Force save the record so we can fetch chatter messages from the back-end
        const saved = await this.props.record.save();
        if (!saved) {
            return;
        }
        await this.aiChatLauncher.openAIChatFromContextV2({
            callerComponentName: 'chatter_ai_button',
            originalRecordModel: this.props.record.resModel,
            originalRecordId: this.props.record.resId,
            originalRecordData: this.props.record.data,
            originalRecordFields: this.props.record.fields,
            aiChatSourceId: this.props.record.resId,
            specialActionCallbacks: {
                sendMessage: (content) => {
                    this.state.thread.composer.text = convertBrToLineBreak(content);
                    this.toggleComposer('message');
                },
                logNote: (content) => {
                    this.state.thread.composer.text = convertBrToLineBreak(content);
                    this.toggleComposer('note');
                }
            },
            placeholderPrompt: _t("Summarize the chatter conversation"),
        });
    },
});
