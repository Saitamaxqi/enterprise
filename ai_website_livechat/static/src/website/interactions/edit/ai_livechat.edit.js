import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";


export class AILivechatEdit extends Interaction {
    static selector = ".s_ai_livechat .ai_livechat_component";

    setup() {
        this.renderAt("ai_website_livechat.s_ai_livechat_edit", {
            livechatAvailable: this.dataEl.attr('livechatChannelId'),
            fallbackButtonURL: this.dataEl.attr('fallbackButtonURL'),
            fallbackButtonText: this.dataEl.attr('fallbackButtonText') || _t('Contact Us')
        }, this.el);
        $('.ai_livechat_prompt_textarea').attr('placeholder', this.dataEl.attr('promptPlaceholder'))
    }
    get dataEl(){
        return $('.s_ai_livechat_data')
    }
}

registry.category("public.interactions.edit").add("ai_website_livechat.ai_livechat_edit", {
    Interaction: AILivechatEdit,
});
