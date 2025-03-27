import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { Record } from "@web/model/relational_model/record";
import {
    asyncStep,
    Command,
    defineModels,
    fields,
    models,
    mountView,
    patchWithCleanup,
    waitForSteps,
} from "@web/../tests/web_test_helpers";

import { beforeEach, expect, test } from "@odoo/hoot";
import { click } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";

class AiModel extends models.Model {
    _name = "ai_model";

    currency_id = fields.Many2one({ relation: "currency" });

    bool = fields.Boolean({ ai: "bool prompt" });
    char = fields.Char({ ai: "char prompt" });
    datetime = fields.Datetime({ ai: "2024-03-26 12:00:00" });
    float = fields.Float({ ai: 42.5 });
    html = fields.Html({ ai: "<p>html prompt</p>" });
    integer = fields.Integer({ ai: 32 });
    many2many = fields.Many2many({ ai: [Command.set([1, 2])], relation: "ai_model" });
    many2one = fields.Many2one({ ai: { id: 2, display_name: "ai_model,2" }, relation: "ai_model" });
    monetary = fields.Monetary({ ai: 99.99, currency_field: "currency_id" });
    selection = fields.Selection({
        ai: "v2",
        selection: [
            ["v1", "Val 1"],
            ["v2", "Val 2"],
        ],
    });
    text = fields.Text({ ai: "text prompt" });

    _records = [{ id: 1 }, { id: 2 }];

    async get_ai_field_value(rec, fieldName, changes) {
        const field = this._fields[fieldName];
        if (!field) {
            throw new Error("Unknown field " + fieldName);
        }
        if (field.type === "boolean") {
            return true;
        } else if (["char", "text", "html"].includes(field.type)) {
            return field.ai;
        } else {
            return field.ai;
        }
    }
}

class Currency extends models.Model {
    _name = "currency";
}

defineModels([AiModel, Currency]);
defineMailModels();

beforeEach(() => {
    patchWithCleanup(Record.prototype, {
        async computeAiField(fname) {
            const res = await super.computeAiField(fname);
            asyncStep(fname + " computed");
            return res;
        },

        async save(options) {
            const res = await super.save(options);
            asyncStep("save");
            return res;
        },
    });
});

test("AI Fields - Boolean Field", async () => {
    await mountView({
        type: "form",
        resId: 1,
        resModel: "ai_model",
        arch: `<form>
                    <field name="bool" widget="ai_boolean"/>
                </form>`,
    });
    expect(".o_field_ai_boolean").toHaveCount(1);
    expect(".o_field_ai_boolean input").not.toBeChecked();
    expect(".o_field_ai_boolean .btn[title='Refresh value']").toHaveCount(1);
    await click(".o_field_ai_boolean .btn[title='Refresh value']");
    await waitForSteps(["bool computed"]);
    await animationFrame();
    await animationFrame();
    expect(".o_field_ai_boolean input").toBeChecked();
    await click(".o_form_button_save");
    await waitForSteps(["save"]);
    await animationFrame();
    expect(".o_field_ai_boolean input").toBeChecked();
});

test("AI Fields - Char Field", async () => {
    await mountView({
        type: "form",
        resId: 1,
        resModel: "ai_model",
        arch: `<form>
                    <field name="char" widget="ai_char"/>
                </form>`,
    });
    expect(".o_field_ai_char").toHaveCount(1);
    expect(".o_field_ai_char input").toHaveValue("");
    expect(".o_field_ai_char .btn[title='Refresh value']").toHaveCount(1);
    await click(".o_field_ai_char .btn[title='Refresh value']");
    await waitForSteps(["char computed"]);
    await animationFrame();
    expect(".o_field_ai_char input").toHaveValue("char prompt");
    await click(".o_form_button_save");
    await waitForSteps(["save"]);
    await animationFrame();
    expect(".o_field_ai_char input").toHaveValue("char prompt");
});

test("AI Fields - Datetime Field", async () => {
    await mountView({
        type: "form",
        resId: 1,
        resModel: "ai_model",
        arch: `<form>
                    <field name="datetime" widget="ai_datetime"/>
                </form>`,
    });
    expect(".o_field_ai_datetime").toHaveCount(1);
    expect(".o_field_ai_datetime input").toHaveValue("");
    expect(".o_field_ai_datetime .btn[title='Refresh value']").toHaveCount(1);
    await click(".o_field_ai_datetime .btn[title='Refresh value']");
    await waitForSteps(["datetime computed"]);
    await animationFrame();
    expect(".o_field_ai_datetime input").toHaveValue("03/26/2024 13:00");
    await click(".o_form_button_save");
    await waitForSteps(["save"]);
    await animationFrame();
    expect(".o_field_ai_datetime input").toHaveValue("03/26/2024 13:00");
});

test("AI Fields - Float Field", async () => {
    await mountView({
        type: "form",
        resId: 1,
        resModel: "ai_model",
        arch: `<form>
                    <field name="float" widget="ai_float"/>
                </form>`,
    });
    expect(".o_field_ai_float").toHaveCount(1);
    expect(".o_field_ai_float input").toHaveValue("0.00");
    expect(".o_field_ai_float .btn[title='Refresh value']").toHaveCount(1);
    await click(".o_field_ai_float .btn[title='Refresh value']");
    await waitForSteps(["float computed"]);
    await animationFrame();
    expect(".o_field_ai_float input").toHaveValue("42.50");
    await click(".o_form_button_save");
    await waitForSteps(["save"]);
    await animationFrame();
    expect(".o_field_ai_float input").toHaveValue("42.50");
});

test("AI Fields - Html Field", async () => {
    await mountView({
        type: "form",
        resId: 1,
        resModel: "ai_model",
        arch: `<form>
                    <field name="html" widget="ai_html"/>
                </form>`,
    });
    expect(".o_field_ai_html").toHaveCount(1);
    expect(".o_field_ai_html .odoo-editor-editable").toHaveText("");
    expect(".o_field_ai_html .btn[title='Refresh value']").toHaveCount(1);
    await click(".o_field_ai_html .btn[title='Refresh value']");
    await waitForSteps(["html computed"]);
    await animationFrame();
    await animationFrame();
    expect(".o_field_ai_html .odoo-editor-editable p").toHaveText("html prompt");
    await click(".o_form_button_save");
    await waitForSteps(["save"]);
    await animationFrame();
    expect(".o_field_ai_html .odoo-editor-editable p").toHaveText("html prompt");
});

test("AI Fields - Integer Field", async () => {
    await mountView({
        type: "form",
        resId: 1,
        resModel: "ai_model",
        arch: `<form>
                    <field name="integer" widget="ai_integer"/>
                </form>`,
    });
    expect(".o_field_ai_integer").toHaveCount(1);
    expect(".o_field_ai_integer input").toHaveValue("0");
    expect(".o_field_ai_integer .btn[title='Refresh value']").toHaveCount(1);
    await click(".o_field_ai_integer .btn[title='Refresh value']");
    await waitForSteps(["integer computed"]);
    await animationFrame();
    expect(".o_field_ai_integer input").toHaveValue("32");
    await click(".o_form_button_save");
    await waitForSteps(["save"]);
    await animationFrame();
    expect(".o_field_ai_integer input").toHaveValue("32");
});

test("AI Fields - Many2ManyTags Field", async () => {
    await mountView({
        type: "form",
        resId: 1,
        resModel: "ai_model",
        arch: `<form>
                    <field name="many2many" widget="ai_many2many_tags"/>
                </form>`,
    });
    expect(".o_field_ai_many2many_tags").toHaveCount(1);
    expect(".o_field_ai_many2many_tags .o_tag").toHaveCount(0);
    expect(".o_field_ai_many2many_tags .btn[title='Refresh value']").toHaveCount(1);
    await click(".o_field_ai_many2many_tags .btn[title='Refresh value']");
    await waitForSteps(["many2many computed"]);
    await animationFrame();
    expect(".o_field_ai_many2many_tags .o_tag").toHaveCount(2);
    expect(".o_field_ai_many2many_tags .o_tag:first").toHaveText("ai_model,1");
    expect(".o_field_ai_many2many_tags .o_tag:last").toHaveText("ai_model,2");
    await click(".o_form_button_save");
    await waitForSteps(["save"]);
    await animationFrame();
    expect(".o_field_ai_many2many_tags .o_tag").toHaveCount(2);
    expect(".o_field_ai_many2many_tags .o_tag:first").toHaveText("ai_model,1");
    expect(".o_field_ai_many2many_tags .o_tag:last").toHaveText("ai_model,2");
});

test("AI Fields - Many2One Field", async () => {
    await mountView({
        type: "form",
        resId: 1,
        resModel: "ai_model",
        arch: `<form>
                    <field name="many2one" widget="ai_many2one"/>
                </form>`,
    });
    expect(".o_field_ai_many2one").toHaveCount(1);
    expect(".o_field_ai_many2one input").toHaveValue("");
    expect(".o_field_ai_many2one .btn[title='Refresh value']").toHaveCount(1);
    await click(".o_field_ai_many2one .btn[title='Refresh value']");
    await waitForSteps(["many2one computed"]);
    await animationFrame();
    expect(".o_field_ai_many2one input").toHaveValue("ai_model,2");
    await click(".o_form_button_save");
    await waitForSteps(["save"]);
    await animationFrame();
    expect(".o_field_ai_many2one input").toHaveValue("ai_model,2");
});

test("AI Fields - Monetary Field", async () => {
    await mountView({
        type: "form",
        resId: 1,
        resModel: "ai_model",
        arch: `<form>
                    <field name="monetary" widget="ai_monetary" options="{'currency_field': 'currency_id'}"/>
                </form>`,
    });
    expect(".o_field_ai_monetary").toHaveCount(1);
    expect(".o_field_ai_monetary input").toHaveValue("0.00");
    expect(".o_field_ai_monetary .btn[title='Refresh value']").toHaveCount(1);
    await click(".o_field_ai_monetary .btn[title='Refresh value']");
    await waitForSteps(["monetary computed"]);
    await animationFrame();
    expect(".o_field_ai_monetary input").toHaveValue("99.99");
    await click(".o_form_button_save");
    await waitForSteps(["save"]);
    await animationFrame();
    expect(".o_field_ai_monetary input").toHaveValue("99.99");
});

test("AI Fields - Selection Field", async () => {
    await mountView({
        type: "form",
        resId: 1,
        resModel: "ai_model",
        arch: `<form>
                    <field name="selection" widget="ai_selection"/>
                </form>`,
    });
    expect(".o_field_ai_selection").toHaveCount(1);
    expect(".o_field_ai_selection select").toHaveValue("false");
    expect(".o_field_ai_selection .btn[title='Refresh value']").toHaveCount(1);
    await click(".o_field_ai_selection .btn[title='Refresh value']");
    await waitForSteps(["selection computed"]);
    await animationFrame();
    expect(".o_field_ai_selection select").toHaveValue('"v2"');
    await click(".o_form_button_save");
    await waitForSteps(["save"]);
    await animationFrame();
    expect(".o_field_ai_selection select").toHaveValue('"v2"');
});

test("AI Fields - Text Field", async () => {
    await mountView({
        type: "form",
        resId: 1,
        resModel: "ai_model",
        arch: `<form>
                    <field name="text" widget="ai_text"/>
                </form>`,
    });
    expect(".o_field_ai_text").toHaveCount(1);
    expect(".o_field_ai_text textarea").toHaveValue("");
    expect(".o_field_ai_text .btn[title='Refresh value']").toHaveCount(1);
    await click(".o_field_ai_text .btn[title='Refresh value']");
    await waitForSteps(["text computed"]);
    await animationFrame();
    expect(".o_field_ai_text textarea").toHaveValue("text prompt");
    await click(".o_form_button_save");
    await waitForSteps(["save"]);
    await animationFrame();
    expect(".o_field_ai_text textarea").toHaveValue("text prompt");
});
