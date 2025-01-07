import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";

/**
 * Restores the user preferred documents view mode ("kanban" or "list").
 * Not applied in mobile environments (uses the "mobile_view_mode"
 * action field which defaults on "kanban").
 */
function documentActionPreference(env, action, options) {
    const viewType = browser.localStorage.getItem("documentsDefaultViewType");
    return env.services.action.doAction("documents.document_action", {
        ...options,
        viewType,
    });
}

registry.category("actions").add("document_action_preference", documentActionPreference);
