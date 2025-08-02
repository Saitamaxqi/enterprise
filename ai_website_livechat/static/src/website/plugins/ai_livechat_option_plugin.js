import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { BuilderAction } from "@html_builder/core/builder_action";

class AILivechatOptionPlugin extends Plugin {
    static id = "aiLivechatOption";
    static dependencies = ["cachedModel"];

    resources = {
        so_content_addition_selector: [".s_ai_livechat"],
        builder_options: [
            {
                template: "ai_website_livechat.AILivechatOption",
                selector: ".s_ai_livechat",
            },
        ],
        builder_actions: {
            SetChatStyleAction,
            SetAIAgentAction,
            SetLivechatChannelAction,
            SetPromptPlaceholderAction,
            SetFallbackButtonTextAction,
            SetFallbackButtonURLAction,
        },
    };
}

export class SetAIAgentAction extends BuilderAction {
    static id = "setAIAgent";
    static dependencies = ["cachedModel"];

    getValue ({ editingElement }) {
        const agentId = editingElement.dataset.agentId;
        if (!agentId) {
            return undefined;
        }
        return JSON.stringify({ id: parseInt(agentId) });
    }

    async load ({ value }) {
        if (!value) {
            return;
        }
        value = JSON.parse(value);
        return this.dependencies.cachedModel.ormSearchRead(
            "ai.agent",
            [["id", "=", parseInt(value.id)]],
            ['partner_id']
        );
    }

    async apply ({ editingElement, value, loadResult }) {
        const id = value ? JSON.parse(value).id : "";
        const oldAgentId = editingElement.dataset.agentId;
        editingElement.dataset.agentId = id;
        const livechatDataEl = editingElement.querySelector(".s_ai_livechat_data");
        livechatDataEl.setAttribute('agentId', id);
        if (loadResult) {
            livechatDataEl.setAttribute('agentPartnerId', loadResult[0]['partner_id'][0]);
        }
        this.use_agent_on_snippet({ newAgentId: id, oldAgentId: oldAgentId })
    }

    clean({ editingElement }) {
        const oldAgentId = editingElement.dataset.agentId;
        editingElement.dataset.agentId = "";
        const livechatDataEl = editingElement.querySelector(".s_ai_livechat_data");
        livechatDataEl.removeAttribute('agentId');
        livechatDataEl.removeAttribute('agentPartnerId');
        this.use_agent_on_snippet({ oldAgentId: oldAgentId })
    }

    async use_agent_on_snippet({ newAgentId=null, oldAgentId=null }){
        let agent_ids = {}
        if(newAgentId){
            agent_ids.new_agent_id = parseInt(newAgentId);
        }
        if(oldAgentId){
            agent_ids.old_agent_id = parseInt(oldAgentId);
        }
        await this.services.orm.call(
            "ai.agent",
            "use_on_website_snippet",
            [],
            agent_ids,
        );
    }
}

export class SetLivechatChannelAction extends BuilderAction {
    static id = "setLivechatChannel";

    getValue ({ editingElement }) {
        const livechatChannelId = editingElement.dataset.livechatChannelId;
        if (!livechatChannelId) {
            return undefined;
        }
        return JSON.stringify({ id: parseInt(livechatChannelId) });
    }

    apply ({ editingElement, value }) {
        const livechatDataEl = editingElement.querySelector(".s_ai_livechat_data");
        const id = value ? JSON.parse(value).id : "";
        editingElement.dataset.livechatChannelId = id;
        livechatDataEl.setAttribute('livechatChannelId', id);
    }

    clean({ editingElement }) {
        editingElement.dataset.livechatChannelId = "";
        const livechatDataEl = editingElement.querySelector(".s_ai_livechat_data");
        livechatDataEl.removeAttribute('livechatChannelId');
    }
}

export class SetChatStyleAction extends BuilderAction {
    static id = "setChatStyle";

    isApplied ({ editingElement, params: { mainParam: chatStyle } }) {
        if (!editingElement.dataset.chatStyle) {
            editingElement.dataset.chatStyle = "fullscreen";
        }
        return editingElement.dataset.chatStyle === chatStyle;
    }

    apply ({ editingElement, params: { mainParam: chatStyle } }) {
        editingElement.dataset.chatStyle = chatStyle;
        editingElement.querySelector(".s_ai_livechat_data").setAttribute('chatStyle', chatStyle);
    }
}

export class SetPromptPlaceholderAction extends BuilderAction {
    static id = "setPromptPlaceholder";

    getValue ({ editingElement }) {
        const promptPlaceholder = editingElement.dataset.promptPlaceholder;
        if (!promptPlaceholder) {
            return "";
        }
        return promptPlaceholder;
    }

    apply ({ editingElement, value }) {
        editingElement.dataset.promptPlaceholder = value;
        editingElement.querySelector(".s_ai_livechat_data").setAttribute('promptPlaceholder', value);
    }
}

export class SetFallbackButtonTextAction extends BuilderAction {
    static id = "setFallbackButtonText";

    getValue ({ editingElement }) {
        const fallbackButtonText = editingElement.dataset.fallbackButtonText;
        if (!fallbackButtonText) {
            return "";
        }
        return fallbackButtonText;
    }

    apply ({ editingElement, value }) {
        editingElement.dataset.fallbackButtonText = value;
        editingElement.querySelector(".s_ai_livechat_data").setAttribute('fallbackButtonText', value);
    }
}

export class SetFallbackButtonURLAction extends BuilderAction {
    static id = "setFallbackButtonURL";

    getValue ({ editingElement }) {
        const fallbackButtonURL = editingElement.dataset.fallbackButtonURL;
        if (!fallbackButtonURL) {
            return "";
        }
        return fallbackButtonURL;
    }

    apply ({ editingElement, value }) {
        editingElement.dataset.fallbackButtonURL = value;
        editingElement.querySelector(".s_ai_livechat_data").setAttribute('fallbackButtonURL', value);
    }
}

registry.category("website-plugins").add(AILivechatOptionPlugin.id, AILivechatOptionPlugin);
