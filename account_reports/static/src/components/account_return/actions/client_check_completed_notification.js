import { registry } from "@web/core/registry"
import { _t } from "@web/core/l10n/translation";

export async function AccountReturnChecksCompletedActionHandler(env, action) {
    const notification = env.services.notification;
    const actionService = env.services.action;
    const params = action.params || {};

    notification.add(
        params.message,
        {
            autocloseDelay: 2500,
            type: 'success',
            buttons: [
                {
                    name: _t("See Checks"),
                    primary: true,
                    onClick: () => {
                        actionService.doAction(params.action);
                    }
                }
            ]
        }
    )

    env.bus.trigger("return_reload_model", {resIds: action.context.active_ids});
}

registry.category("actions").add("action_return_checks_completed_notification", AccountReturnChecksCompletedActionHandler)
