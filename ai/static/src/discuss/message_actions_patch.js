import { patch } from "@web/core/utils/patch";

import { _t } from "@web/core/l10n/translation";
import { registerMessageAction, messageActionsInternal } from "@mail/core/common/message_actions";
import { unwrapContents } from "@html_editor/utils/dom";
import { setElementContent } from "@web/core/utils/html";

registerMessageAction("insertToComposer", {
    condition: (component) =>
        !!component.props.thread.aiSpecialActions?.insert &&
        component.store.aiInsertButtonTarget && // after a reload both parts of the below conditions are undefined and but we don't want to button to appear
        (component.store.aiInsertButtonTarget === component.props.thread.aiChatSource ||
            component.env.isSmall) &&
        !component.message.isSelfAuthored,
    name: _t("Use this"),
    onSelected: (component) => {
        const fragment = document.createDocumentFragment();
        const content_root = document.createElement("span");
        content_root.setAttribute("InsertorId", "AIInsertion");
        setElementContent(content_root, component.props.message.body);
        // check if the content is enclosed in a <p> element, if so, unwrap it
        const paragraphElements = content_root.querySelectorAll("p");
        if (paragraphElements.length === 1) {
            unwrapContents(paragraphElements[0]);
        }
        fragment.appendChild(content_root);
        component.props.thread.aiSpecialActions.insert(fragment);
        if (component.env.isSmall) {
            component.props.thread.closeChatWindow();
        }
    },
    sequence: 10,
});
registerMessageAction("send-message-direct", {
    condition: (component) =>
        !!component.props.thread.aiSpecialActions?.sendMessage && !component.message.isSelfAuthored, // don't show the buttons for the user's messages,
    name: _t("Send as Message"),
    onSelected: (component) => {
        component.props.thread.aiSpecialActions.sendMessage(component.props.message.body);
    },
    sequence: 20,
});
registerMessageAction("log-note-direct", {
    condition: (component) =>
        !!component.props.thread.aiSpecialActions?.logNote && !component.message.isSelfAuthored, // don't show the buttons for the user's messages
    name: _t("Log as Note"),
    onSelected: (component) =>
        component.props.thread.aiSpecialActions.logNote(component.props.message.body),
    sequence: 30,
});

patch(messageActionsInternal, {
    condition(component, id, action) {
        const requiredActions = [
            "insertToComposer",
            "copy-message",
            "send-message-direct",
            "log-note-direct",
        ];
        if (component.props.thread?.channel_type === "ai_chat" && !requiredActions.includes(id)) {
            return false;
        }
        if (id === "copy-message") {
            return (
                super.condition(component, id, action) ||
                component.props.thread?.channel_type === "ai_chat"
            );
        }
        return super.condition(component, id, action);
    },
    sequence(component, id, action) {
        if (id === "copy-message" && component.props.thread?.channel_type === "ai_chat") {
            return 50;
        }
        return super.sequence(component, id, action);
    },
});
