import { registry } from "@web/core/registry";


export async function AccountReturnOpenViewActionHandler(env, action) {
    const actionService = env.services.action;
    const orm = env.services.orm;

    const result = await orm.call(
        "account.return",
        "action_open_tax_return_view",
        []
    )

    if (result){
        actionService.doAction(result);
    }
}

registry.category("actions").add("action_open_view_account_return", AccountReturnOpenViewActionHandler)
