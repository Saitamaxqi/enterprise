import { describe, expect, test } from "@odoo/hoot";
import { serializeDateTime } from "@web/core/l10n/dates";
import { contains, mountView, makeMockServer, serverState } from "@web/../tests/web_test_helpers";
import { defineSignModels, signModels } from "./mock_server/mock_models/sign_model";

const { DateTime } = luxon;

describe.current.tags("desktop");
defineSignModels();

test("list activity widget: sign button in dropdown", async () => {
    const { MailActivity, ResPartner, ResUsers } = signModels;

    const env = await makeMockServer();

    MailActivity._records = [
        {
            id: 1,
            summary: "Sign a new contract",
            activity_category: "sign_request",
            date_deadline: serializeDateTime(DateTime.now().plus({ days: 1 })),
            can_write: true,
            state: "planned",
            user_id: serverState.userId,
            activity_type_id: 1,
        },
    ];

    env.models[ResPartner._name].write([serverState.partnerId], {
        activity_ids: [1],
        activity_state: "today",
    });

    env.models[ResUsers._name].write([serverState.userId], {
        activity_ids: [1],
        activity_summary: "Sign a new contract",
        activity_type_id: 1,
    });

    await mountView({
        type: "list",
        resModel: "res.users",
        arch: `<list>
            <field name="activity_ids" widget="list_activity"/>
        </list>`,
    });
    expect(".o-mail-ListActivity-summary").toHaveText("Sign a new contract");
    await contains(".o-mail-ActivityButton").click(); // open the popover
    expect(".o-mail-ActivityListPopoverItem-markAsDone").toHaveCount(0);
    expect(".o-mail-ActivityListPopoverItem-requestSign").toHaveCount(1);
});
