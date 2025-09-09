import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { useService, useBus } from "@web/core/utils/hooks";
import { Component, onMounted, useState, onWillStart, markup, useEffect, useRef } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { convertBrToLineBreak, prettifyMessageContent } from "@mail/utils/common/format";


export class AILivechatComponent extends Component {
    static template = "ai_website_livechat.AILivechatComponent";
    static props = {
        agentId: { type: Number },
        livechatChannelId: { type: Number, optional: true },
        chatStyle: { type: String, optional: true },
        promptPlaceholder: {type: String, optional: true },
        selectorToHide: { type: Array, element: String, optional: true },
        selectorToHideMobile: { type: Array, element: String, optional: true },
        promptMax: { type: Number, optional: true },
        fallbackButtonText: { type: String },
        fallbackButtonURL: { type: String },
    };
    static defaultProps = {
        selectorToHide: ['footer', '.o-livechat-root', '.support-secondary'],
        promptMax: 500,
    }

    setup() {
        this.notificationService = useService("notification");
        this.store = useService("mail.store");
        this.livechatService = useService("im_livechat.livechat");

        this.state = useState({
            prompt: "",
            messages: [],
        });
        this.promptInputRef = useRef("promptInput");
        this.messagesDiv = useRef("messagesDiv");
        this.thread = undefined;

        onWillStart(this.isLivechatAvailable.bind(this));
        onMounted(() => {
            this.updateUI();
        });

        useBus(this.env.bus, "CHATWINDOW_CLOSED", async (payload) => { await this.onChatWindowClosed(payload) })
        useBus(this.env.bus, "discuss.channel/new_message", this.onMessagePosted.bind(this))
        useEffect(
            () => {
                // Resize  textarea to fit its content.
                this.promptInputRef.el.style.height = 0;
                this.promptInputRef.el.style.height = this.promptInputRef.el.scrollHeight + "px";
            },
            () => [this.state.prompt]
        );
        useEffect(
            () => {
                // Scroll to the latest message whenever new message
                // is inserted.
                const messagesDivEl = this.messagesDiv.el;
                let selectorToHide = this.props.selectorToHide;
                if(messagesDivEl){
                    const lastMessageEl = messagesDivEl.lastElementChild;
                    lastMessageEl.scrollIntoView({ block: "start", inline: "nearest", behavior: "smooth" });
                    if(this.props.selectorToHide){
                        for (const s of selectorToHide) {
                            $(s).addClass('d-none');
                        }
                    }
                    if(this.props.selectorToHideMobile){
                        for (const s of this.props.selectorToHideMobile) {
                            $(s).addClass('d-none');
                            $(s).addClass('d-lg-block');
                        }
                    }
                    this.hideOtherSnippets();
                }
                else{
                    if(this.props.selectorToHide){
                        for (const s of this.props.selectorToHide) {
                            $(s).removeClass('d-none');
                        }
                    }
                    if(this.props.selectorToHideMobile){
                        for (const s of this.props.selectorToHideMobile) {
                            $(s).removeClass('d-none');
                            $(s).removeClass('d-lg-block');
                        }
                    }
                    this.showOtherSnippets();
                }
            },
            () => [this.state.messages.length]
        );
    }

    async isLivechatAvailable(){
        this.livechatAvailable = await rpc(
            "/ai_website_livechat/is_livechat_operator_available",
            {'livechat_channel_id': this.props.livechatChannelId}
        );
    }

    fillStateMessages(){
        if(this.chattingWithHuman){
            return;
        }
        for (const message of [...this.thread.allMessages].reverse() ?? []){
            if(message.isSelfAuthored){
                this.state.messages.push({ author: "user", text: message.body })
            }
            else{
                this.state.messages.push(
                    {
                        author: "assistant",
                        text: message.body,
                        isError: false,
                        id: message.id,
                    }
                ) 
            }
        }
    }

    updateUI(){
        if(this.state.messages.length){
            this.unfreezeInput(); // Otherwise, Ask A Human and Close buttons are disabled.
        }
        if(this.thread && this.props.chatStyle === "fullscreen" && this.thread.ai_agent_id){
            this.hideChatWindow();
        }
    }

    onMessagePosted({ detail: { message } }){
        if(!message.thread?.eq(this.thread) || message.isSelfAuthored){
            return;
        }
        this.processResponse(message);
    }

    processResponse(message){
        if(this.props.chatStyle === "fullscreen" && this.thread.ai_agent_id){
            let messageData = {
                author: "assistant",
                text: message.body,
                isError: false,
                id: message.id,
            };
            const messageIndex = this.state.messages.findIndex((m) => m.id === "assistant_thinking");
            if(messageIndex != -1){
                this.state.messages.splice(messageIndex, 1);
            }
            this.state.messages.push(messageData);
        }
        this.unfreezeInput()
    }

    async onChatWindowClosed({ detail }){
        if(detail.channelId === this.thread?.id){
            // leaveLivechatSession = false => User has already left the livechat session.
            await this.closeConversation(false);
        }
    }

    async closeConversation(leaveLivechatSession=true) {
        this.state.messages = [];
        this.state.prompt = "";
        const thread = this.thread;
        await thread?.closeChatWindow({ notifyState: true, force: true });
        if(leaveLivechatSession && thread?.channel_type === 'livechat'){
            await this.livechatService.leave(thread);
        }
        this.thread = undefined;
    }

    showOtherSnippets() {
        const snippetFullscreenClass = "s_ai_livechat_fullscreen"
        const aiLivechatSnippet = document.querySelector('.s_ai_livechat');
        if(aiLivechatSnippet){
            const elementsToHide = document.querySelectorAll(`#wrap:has(.${snippetFullscreenClass}) > :not(.${snippetFullscreenClass})`);
            for (const el of elementsToHide) {
                el.classList.remove("d-none");
            }
            aiLivechatSnippet.classList.remove(snippetFullscreenClass);
        }
    }

    hideOtherSnippets() {
        const snippetFullscreenClass = "s_ai_livechat_fullscreen"
        const aiLivechatSnippet = document.querySelector('.s_ai_livechat');
        if(aiLivechatSnippet){
            aiLivechatSnippet.classList.add(snippetFullscreenClass);
            const elementsToHide = document.querySelectorAll(`#wrap:has(.${snippetFullscreenClass}) > :not(.${snippetFullscreenClass})`);
            for (const el of elementsToHide) {
                el.classList.add("d-none");
            }
        }
    }

    onTextareaKeydown(ev) {
        if(ev.key === "Enter" && !ev.shiftKey){
            ev.stopImmediatePropagation();
            if(this.state.prompt.trim().length){
                this.submitPrompt(ev);
            }
        }
    }

    async submitPrompt(ev) {
        if(!this.props.agentId){
            this.notificationService.add(_t("Oops, there is no Agent linked to this block!"));
            return;
        }
        if(this.thread && !this.thread.ai_agent_id){
            return;
        }
        this.freezeInput();
        if(ev){
            ev.preventDefault();
        }
        await this.createThread();
        if(!this.isThreadActive){
            this.unfreezeInput();
            this.notificationService.add(_t("An error occurred. Please try again."));
            return;
        }
        const prompt = this.state.prompt;
        this.thread?.post(prompt);
        this.state.prompt = "";
        if(this.props.chatStyle === "popup"){
            this.thread.openChatWindow({ focus:true })
        }
        if(this.props.chatStyle === "fullscreen"){
            this.state.messages.push({ author: "user", text: await prettifyMessageContent(prompt) });
            this.state.messages.push({ author: "assistant", id: "assistant_thinking" });
        }
    }

    freezeInput() {
        this.promptInputRef.el.setAttribute("disabled", "");
        if(this.state.messages.length){
            $(".o-disable-thinking").attr("disabled", "");
        }
    }

    unfreezeInput() {
        this.promptInputRef.el.removeAttribute("disabled");
        if(this.state.messages.length){
            $(".o-disable-thinking").removeAttr("disabled");
        }
        this.promptInputRef.el.focus();
    }

    async createThread(){
        if(this.isThreadActive){
            return;
        }
        if(this.livechatAvailable){
            let livechatThreadOptions = { persist: true, channel_id: this.props.livechatChannelId, ai_agent_id: this.props.agentId };
            this.thread = await this.livechatService._createThread({ options: livechatThreadOptions })
        }
        else{
            let channel_params = { ai_agent_id: this.props.agentId }
            const result = await rpc("/ai_website_livechat/create_chat_channel", channel_params);
            if (!result) {
                return;
            }
            this.store.insert(result["store_data"]);
            this.thread = this.store.Thread.get({ id: result["channel_id"], model: "discuss.channel" });
        }
        if (!this.thread.ai_agent_id) {
            this.thread = undefined;
        }
    }

    async askHuman(ev) {
        await this.createThread()
        if (!this.isThreadActive || !this.thread.ai_agent_id){
            return;
        }
        const result = await rpc("/ai_livechat/forward_operator", {
            channel_id: this.thread.id,
        });
        if(result['store_data']){
            this.store.insert(result['store_data']);
        }
        if(result['notification']){
            this.store.env.services.notification.add(result['notification'], { type: result['notification_type']});
        }
        if(result['success'] === true){
            this.thread.readyToSwapDeferred.resolve();
            this.showChatWindow()
        }
    }

    showChatWindow(){
        $('.o-livechat-root').removeClass('d-none');
        this.thread.openChatWindow()
    }

    hideChatWindow(){
        let chatWindow = this.store.ChatWindow.get({ thread: this.thread });
        if(!chatWindow){
            return;
        }
        this.store.chatHub.opened.delete(chatWindow);
        this.store.chatHub.folded.delete(chatWindow);
        this.store.chatHub.save();
    }

    async copyAnswer(ev) {
        const message_index = parseInt($(ev.currentTarget).data('message-id'));
        const message_content_markdown = convertBrToLineBreak(this.state.messages[message_index].text);
        const message_content_html = this.state.messages[message_index].text;
        await browser.navigator.clipboard?.write([
            new ClipboardItem({
                'text/html': new Blob([message_content_html], {type: 'text/html'}),
                'text/plain': new Blob([message_content_markdown], {type: 'text/plain'}),
            }),
        ]);
    }

    formatContent(content) {
        const result = DOMPurify.sanitize(content);
        return markup(result);
    }

    get isThreadActive(){
        return Boolean(
            this.thread
            && (
                this.thread.channel_type === 'ai_chat'
                ||
                this.thread.channel_type == 'livechat' && !this.thread.livechat_end_dt
            )
        )
    }
}
registry.category("public_components").add("ai_website_livechat.ai_livechat_component", AILivechatComponent);
