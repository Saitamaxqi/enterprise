import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { AILivechatComponent } from "@ai_website_livechat/website/components/ai_livechat_component/ai_livechat";
import { _t } from "@web/core/l10n/translation";


export class AILivechat extends Interaction {
    static selector = ".s_ai_livechat";
    dynamicContent = {
        ".ai_livechat_component": {
            "t-component": () => {
                const el = this.el.querySelector(".s_ai_livechat_data");
                return [
                    AILivechatComponent, 
                    {
                        'chatStyle': el.getAttribute('chatStyle') ? el.getAttribute('chatStyle') : 'fullscreen',
                        'agentId': parseInt(el.getAttribute('agentId')),
                        'livechatChannelId': parseInt(el.getAttribute('livechatChannelId')),
                        'promptPlaceholder': el.getAttribute('promptPlaceholder') ? el.getAttribute('promptPlaceholder') : _t('Ask AI'),
                        'fallbackButtonText': el.getAttribute('fallbackButtonText') ? el.getAttribute('fallbackButtonText') : _t('Contact Us'),
                        'fallbackButtonURL': el.getAttribute('fallbackButtonURL'),
                    }
                ]
            }
        }
    };
}

registry.category("public.interactions").add("ai_website_livechat.ai_livechat", AILivechat);
