import { before, expect, test } from "@odoo/hoot";
import {
    contains,
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
} from "@web/../tests/web_test_helpers";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";

class ApprovalModel extends models.Model {
    async get_views() {
        const res = await super.get_views(...arguments);
        res.models[this._name].has_approval_rules = true;
        return res;
    }
}

class Partner extends ApprovalModel {
    display_name = fields.Char();
    image = fields.Binary();
    empty_image = fields.Binary();

    _records = [
        {
            id: 1,
            display_name: "jean",
        },
    ];
}

function getAllRules() {
    return {
        43: {
            id: 43,
            name: false,
            message: false,
            exclusive_user: true,
            can_validate: false,
            action_id: false,
            method: "my_method",
            approver_ids: [6],
            users_to_notify: [],
            approval_group_id: false,
            notification_order: "1",
            domain: false,
        },
        2: {
            id: 2,
            name: false,
            message: false,
            exclusive_user: true,
            can_validate: false,
            action_id: false,
            method: "my_method",
            approver_ids: [6],
            users_to_notify: [],
            approval_group_id: false,
            notification_order: "1",
            domain: false,
        },
        3: {
            id: 3,
            name: false,
            message: false,
            exclusive_user: true,
            can_validate: true,
            action_id: false,
            method: "my_method",
            approver_ids: [6],
            users_to_notify: [],
            approval_group_id: false,
            notification_order: "2",
            domain: false,
        },
    };
}

defineModels([Partner]);
defineMailModels();

let ALL_RULES;
let MODEL_ENTRIES;
before(() => {
    ALL_RULES = getAllRules();
    MODEL_ENTRIES = {
        partner: [
            [
                [1, "my_method", false],
                {
                    rules: [43, 2, 3],
                    entries: [
                        {
                            id: 67,
                            approved: true,
                            user_id: [77, "Mitchell Admin"],
                            write_date: "2024-09-25 08:45:36",
                            rule_id: [43, "Step 1"],
                            model: "sale.order",
                            res_id: 1,
                        },
                    ],
                },
            ],
        ],
    };
});

onRpc("studio.approval.rule", "get_approval_spec", async (...args) => {
    return {
        all_rules: { ...ALL_RULES },
        ...MODEL_ENTRIES,
    };
});

test("approval can revoke below rules", async () => {
    onRpc("studio.approval.rule", "delete_approval", (args) => {
        expect.step({ ruleIds: args.args[0], res_id: args.kwargs.res_id });
        return true;
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `<form>
            <button type="object" name="my_method" />
            </form>
        `,
        resId: 1,
    });
    await contains(".o_web_studio_approval").click();
    expect(".o_web_approval_cancel").toHaveCount(1);
    expect(".o_web_studio_approval_rule:eq(0) .o_web_approval_cancel").toHaveCount(1);
    await contains(".o_web_approval_cancel").click();
    expect.verifySteps([
        {
            res_id: 1,
            ruleIds: [43],
        },
    ]);
});
