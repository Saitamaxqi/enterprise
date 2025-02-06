import { registry } from "@web/core/registry";

async function initChat(env, action) {
    const store = env.services["mail.store"];

    const thread = await store.Thread.getOrFetch({
        model: "discuss.channel",
        id: Number(action.params.channelId),
    });

    thread?.open({ focus: true });
}

registry.category("actions").add("agent_chat_action", initChat);
