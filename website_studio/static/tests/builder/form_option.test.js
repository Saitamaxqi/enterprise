import { expect, test } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";
import { defineWebsiteModels, setupWebsiteBuilder } from "@website/../tests/builder/website_helpers";
import { patch } from "@web/core/utils/patch";
import { IrModel } from "@web/../tests/_framework/mock_server/mock_models/ir_model";

const formSpecRecords = [{
    id: 123,
    model: "website_studio.custom_stuff",
    name: "Custom stuff",
    state: "base",
    website_form_label: "Create some stuff",
    website_form_key: "",
},
{
    id: 85,
    model: "res.partner",
    name: "Contact",
    state: "base",
    website_form_label: "Create a Customer",
    website_form_key: "create_customer",
},
{
    id: 184,
    model: "mail.mail",
    name: "Outgoing Mails",
    state: "base",
    website_form_label: "Send an E-mail",
    website_form_key: "send_mail",
}];

patch(IrModel.prototype, {
    get_compatible_form_models() {
        return formSpecRecords;
    },
    get_views() {
        const result = super.get_views(...arguments);
        result.views.list.arch = `
            <list>
                <field name="name"/>
                <field name="model"/>
                <field name="state"/>
            </list>
        `;
        return result;
    },
    web_search_read() {
        return {
            length: formSpecRecords.length,
            records: formSpecRecords,
        };
    },
});

defineWebsiteModels();

test("change action to Mode models", async () => {
    await setupWebsiteBuilder(
        `<section class="s_website_form"><form data-model_name="mail.mail">
            <div class="s_website_form_field"><label class="s_website_form_label" for="contact1">Name</label><input id="contact1" class="s_website_form_input"/></div>
            <div class="s_website_form_submit">
                <div class="s_website_form_label"/>
                <a>Submit</a>
            </div>
        </form></section>`
    );

    await contains(":iframe section").click();
    await contains("div:has(>span:contains('Action')) + div button").click();
    await contains("div.o-dropdown-item:contains('More models')").click();
    await contains(".o_data_cell:contains('Custom stuff')").click();
    expect(":iframe form .s_website_form_field").toHaveCount(0);
    expect(":iframe form .s_website_form_submit").toHaveCount(1);
});
