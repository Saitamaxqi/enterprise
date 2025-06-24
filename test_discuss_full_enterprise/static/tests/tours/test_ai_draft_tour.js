import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

registry.category("web_tour.tours").add('test_ai_draft_chatter_button', {
    steps: () => [stepUtils.showAppsMenuItem(), {
        trigger: ".o_app[data-menu-xmlid='project.menu_main_pm']",
        run: "click",
    }, {
        content: "Open the test project",
        trigger: ".o_kanban_view .o_kanban_record:contains(Test Project)",
        run: "click",
    }, {
        content: "Open the test task",
        trigger: ".o_kanban_view .o_kanban_record:contains(Test Task)",
        run: "click",
    }, {
        content: "Click on the chatter's AI button",
        trigger: "button.btn-ai-chatter",
        run: "click",
    }, {
        content: "Click on the send button to send the AI the default message",
        trigger: "button[name='send-message']",
        run: "click",
    }, {
        content: "Check that the default message is shown",
        trigger: ".o-mail-Message-body:contains('Summarize the chatter conversation')",
    }, {
        content: "Check that the AI gives a reply",
        trigger: ".o-mail-Message-body:has(p:contains('This is dummy ai response'))",
    }, {
        content: "Hover over the user message so its action buttons appear",
        trigger: ".o-mail-Message:eq(1)",
        run: "hover",
    }, {
        content: "Check that the user message has the copy button",
        trigger: ".o-mail-Message:eq(1):has(button[name='copy-message'])",
    }, {
        content: "Check that the user message doesn't have the send message button",
        trigger: ".o-mail-Message:eq(1):not(:has(button[name='send-message-direct']))",
    }, {
        content: "Check that the user message doesn't have the log note button",
        trigger: ".o-mail-Message:eq(1):not(:has(button[name='log-note-direct']))",
    }, {
        content: "Hover over the AI message so its action buttons appear",
        trigger: ".o-mail-Message:eq(2)",
        run: "hover",
    }, {
        content: "Check that the AI message has the copy button",
        trigger: ".o-mail-Message:eq(2):has(button[name='copy-message'])",
    }, {
        content: "Check that the AI message has the send message button",
        trigger: ".o-mail-Message:eq(2):has(button[name='send-message-direct'])",
    }, {
        content: "Check that the AI message has the log note button",
        trigger: ".o-mail-Message:eq(2):has(button[name='log-note-direct'])",
    }, {
        content: "Hover over the AI message so the action buttons appear",
        trigger: ".o-mail-Message:eq(2)",
        run: "hover",
    }, {
        content: "Click on the send message button",
        trigger: "button[name='send-message-direct']",
        run: "click",
    }, {
        content: "The send message chatter button should be activated",
        trigger: ".o-mail-Chatter-sendMessage.active",
    }, {
        content: "Hover over the AI message so the action buttons appear",
        trigger: ".o-mail-Message:eq(2)",
        run: "hover",
    }, {
        content: "Click on the log note button",
        trigger: "button[name='log-note-direct']",
        run: "click",
    }, {
        content: "The log note chatter button should be activated",
        trigger: ".o-mail-Chatter-logNote.active",
    }, {
        content: "Click on the 'log' chatter button",
        trigger: ".o-mail-Composer-send",
        run: "click",
    }, {
        content: "Check the the AI response was actually posted as a note",
        trigger: ".o-mail-Message-body:eq(0):has(p:contains('This is dummy ai response'))",
    }]
});

registry.category("web_tour.tours").add('test_ai_draft_html_field', {
    steps: () => [stepUtils.showAppsMenuItem(), {
        trigger: ".o_app[data-menu-xmlid='project.menu_main_pm']",
        run: "click",
    }, {
        content: "Open the test project",
        trigger: ".o_kanban_view .o_kanban_record:contains(Test Project)",
        run: "click",
    }, {
        content: "Open the test task",
        trigger: ".o_kanban_view .o_kanban_record:contains(Test Task)",
        run: "click",
    }, {
        content: "Click on the HTML editor to show power buttons",
        trigger: ".note-editable",
        run: "click",
    }, {
        content: "Click on the ai powerbutton item",
        trigger: ".power_button:has(span:contains('AI'))",
        run: "click",
    }, {
        content: "Check that the chat window appears",
        trigger: ".o-mail-ChatWindow.o-isAiComposer",
    }, {
        content: "Write a message for the AI",
        trigger: "textarea.o-mail-Composer-input",
        run: "edit Generic prompt to AI",
    }, {
        content: "Click on the send button to send the AI the default message",
        trigger: "button[name='send-message']",
        run: "click",
    }, {
        content: "Check that the AI gives a reply",
        trigger: ".o-mail-Message-body:has(p:contains('This is dummy ai response'))",
    }, {
        content: "Hover over the user message so its action buttons appear",
        trigger: ".o-mail-Message:eq(1)",
        run: "hover",
    }, {
        content: "Check that the user message has the copy button",
        trigger: ".o-mail-Message:eq(1):has(button[name='copy-message'])",
    }, {
        content: "Check that the user message doesn't have the insert button",
        trigger: ".o-mail-Message:eq(1):not(:has(button[name='insertToComposer']))",
    }, {
        content: "Hover over the AI message so its action buttons appear",
        trigger: ".o-mail-Message:eq(2)",
        run: "hover",
    }, {
        content: "Check that the AI message has the copy button",
        trigger: ".o-mail-Message:eq(2):has(button[name='copy-message'])",
    }, {
        content: "Check that the AI message has the insert button",
        trigger: ".o-mail-Message:eq(2):has(button[name='insertToComposer'])",
    }, {
        content: "Hover over the AI message so the action button appear",
        trigger: ".o-mail-Message:eq(2)",
        run: "hover",
    }, {
        content: "Click on the send message button",
        trigger: "button[name='insertToComposer']",
        run: "click",
    }, {
        content: "Check the the AI response was actually inserted in the HTML field ",
        trigger: ".note-editable:has(div:contains('This is dummy ai response'))",
    }]
});
