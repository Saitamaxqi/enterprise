import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { AiPrompt } from "@ai_fields/ai_prompt/ai_prompt";
import { setSelection } from "@html_editor/../tests/_helpers/selection";
import { insertText } from "@html_editor/../tests/_helpers/user_actions";
import {
    defineModels,
    fields,
    models,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";

import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { click, queryOne } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";

class Dummy extends models.Model {
    _name = "dummy";

    name = fields.Char();
    message_ids = fields.One2many({ relation: "mail.message", string: "Messages" });

    async mail_allowed_qweb_expressions() {
        return ["object.display_name"];
    }

    async ai_find_default_records(comodel, domain, field_name, property_name) {
        return [];
    }

    _records = [
        { id: 1, name: "Bob" },
        { id: 2, name: "Patrick" },
        { id: 3, name: "Sheldon" },
    ];
}

defineMailModels();
defineModels([Dummy]);

describe.current.tags("desktop");

let htmlEditor;
beforeEach(() => {
    patchWithCleanup(AiPrompt.prototype, {
        onEditorLoad(editor) {
            htmlEditor = editor;
            return super.onEditorLoad(...arguments);
        },
    });
});

test("AI Prompt - Readonly", async () => {
    await mountWithCleanup(AiPrompt, {
        props: {
            readonly: true,
            prompt: "<p>Hello <t t-out='object.name'>World</t></p>",
            onChange: () => {},
        },
    });
    expect("span.o_readonly_ai_prompt").toHaveCount(1);
    expect("span.o_readonly_ai_prompt").toHaveText("Hello World");
});

test("AI Prompt - Editable", async () => {
    await mountWithCleanup(AiPrompt, {
        props: {
            model: "dummy",
            onChange: (change) => expect.step("change " + change),
            prompt: "<p>Hello <t t-out='object.name'>World</t></p>",
        },
    });
    expect("div.o_ai_prompt").toHaveCount(1);
    expect("div.o_ai_prompt").toHaveText("Hello World");
    setSelection({ anchorNode: queryOne(".o_ai_prompt .odoo-editor-editable p"), anchorOffset: 2 });
    await insertText(htmlEditor, " bloups");
    expect("div.o_ai_prompt").toHaveText("Hello World bloups");
    await click(document.body);
    expect.verifySteps(['change <p>Hello <t t-out="object.name">World</t> bloups</p>']);
});

test("AI Prompt - Field selector without template editor group", async () => {
    onRpc("has_group", () => false);
    await mountWithCleanup(AiPrompt, {
        props: {
            model: "dummy",
            onChange: (change) => expect.step("change " + change),
            prompt: "<p>Hello</p>",
        },
    });
    setSelection({ anchorNode: queryOne(".o_ai_prompt .odoo-editor-editable p"), anchorOffset: 1 });
    await insertText(htmlEditor, " /fie");
    await animationFrame();
    expect(".o-we-command").toHaveCount(1);
    expect(".o-we-command .o-we-command-name").toHaveText("Field Selector");
    await click(".o-we-command");
    await animationFrame();
    // focus moved out of editable, onchange triggered
    expect.verifySteps(["change <p>Hello </p>"]);
    // only displayname available (see mail_allowed_qweb_expressions)
    expect(".o_model_field_selector_popover_item").toHaveCount(1);
    expect(".o_model_field_selector_popover_item_name").toHaveText("Display name");
    await click(".o_model_field_selector_popover_item_name");
    await animationFrame();
    expect("div.o_ai_prompt").toHaveText("Hello Display name");
    // clicking on the record should reopen the field selector
    await click("div.o_ai_prompt .o_ai_field");
    await animationFrame();
    expect(".o_model_field_selector_popover").toHaveCount(1);
    await click(document.body);
    expect.verifySteps([
        'change <p>Hello <span data-oe-protected="true" class="o_ai_field"><span class="d-none">{"display_name":</span><t t-out="object.display_name">Display name</t><span class="d-none">}</span></span> </p>',
    ]);
});

test("AI Prompt - Field selector with template editor group", async () => {
    await mountWithCleanup(AiPrompt, {
        props: {
            model: "dummy",
            onChange: (change) => expect.step("change " + change),
            prompt: "<p>Hello</p>",
        },
    });
    setSelection({ anchorNode: queryOne(".o_ai_prompt .odoo-editor-editable p"), anchorOffset: 1 });
    await insertText(htmlEditor, " /fiel");
    await animationFrame();
    await click(".o-we-command");
    await animationFrame();
    // focus move out of editable, onchange triggered
    expect.verifySteps(["change <p>Hello </p>"]);
    await click(".o_model_field_selector_popover_item_name:contains('Created on')");
    await animationFrame();
    await expect(".o_model_field_selector_popover .badge").toHaveCount(1);
    await expect(".o_model_field_selector_popover .badge").toHaveText("Created on");
    await expect(".o_model_field_selector_popover_item_name:contains('Created on')").toHaveCount(0);
    await click(".o_model_field_selector_popover_item_name:contains('Display name')");
    await animationFrame();
    await expect(".o_model_field_selector_popover .badge").toHaveCount(2);
    await click(".btn-primary");
    await animationFrame();
    expect("div.o_ai_prompt").toHaveText(/Hello\s+Created on\s+Display name/);
    // clicking on the record should reopen the field selector
    await click("div.o_ai_prompt .o_ai_field");
    await animationFrame();
    expect(".o_model_field_selector_popover").toHaveCount(1);
    await click(document.body);
    expect.verifySteps([
        `change <p>Hello </p><div t-out="object._ai_read('create_date','display_name')" class="o_ai_field"><span data-ai-field="create_date">Created on</span><br><span data-ai-field="display_name">Display name</span><br></div><p><br></p>`
    ]);
});

test("AI prompt - Insert messages", async () => {
    await mountWithCleanup(AiPrompt, {
        props: {
            model: "dummy",
            onChange: (change) => expect.step("change " + change),
            prompt: "<p>Messages</p>",
        },
    });
    setSelection({ anchorNode: queryOne(".o_ai_prompt .odoo-editor-editable p"), anchorOffset: 1 });
    await insertText(htmlEditor, " /fiel");
    await animationFrame();
    await click(".o-we-command");
    await animationFrame();
    // focus move out of editable, onchange triggered
    expect.verifySteps(["change <p>Messages </p>"]);
    await click(".o_model_field_selector_popover_item_name:contains('Messages')");
    await animationFrame();
    await click(".btn-primary");
    await animationFrame();
    expect("div.o_ai_prompt").toHaveText("Messages Messages");
    await click(document.body);
    expect.verifySteps([
        'change <p>Messages <t data-ai-field="message_ids" t-out="object.message_ids._ai_format_mail_messages()" class="o_ai_field">Messages</t> </p>',
    ]);
});

test("AI Prompt - Without comodel", async () => {
    await mountWithCleanup(AiPrompt, {
        props: {
            model: "dummy",
            onChange: (change) => expect.step("change " + change),
            prompt: "<p>Hello <t t-out='object.name'>World</t></p>",
        },
    });
    setSelection({ anchorNode: queryOne(".o_ai_prompt .odoo-editor-editable p"), anchorOffset: 1 });
    await insertText(htmlEditor, "/rec");
    await animationFrame();
    // record selector should not be shown
    expect(".o-we-command").toHaveCount(0);
});

test("AI Prompt - With comodel", async () => {
    await mountWithCleanup(AiPrompt, {
        props: {
            comodel: "dummy",
            domain: "[['id', 'in', [1, 2]]]",
            model: "dummy",
            onChange: (change) => expect.step("change " + change),
            prompt: "<p>Hello</p>",
        },
    });
    setSelection({ anchorNode: queryOne(".o_ai_prompt .odoo-editor-editable p"), anchorOffset: 1 });
    insertText(htmlEditor, " /rec");
    await animationFrame();
    expect(".o-we-command").toHaveCount(1);
    expect(".o-we-command-name").toHaveText("Records Selector");
    await click(".o-we-command");
    await animationFrame();
    // focus moved out of editable, onchange triggered
    expect.verifySteps([
        'change <p>Hello </p><div class="o_ai_record o_ai_default_record" data-oe-protected="true" contenteditable="false"><div class="d-none"></div><span>0 records</span></div>',
    ]);
    await animationFrame();
    await click(".o_records_selector_popover input");
    await animationFrame();
    // filtered using the domain
    expect(".o-autocomplete--dropdown-item").toHaveCount(2);
    await click(".o-autocomplete--dropdown-item:contains('Bob')");
    await animationFrame();
    await click(".o_records_selector_popover input");
    await animationFrame();
    expect(".o-autocomplete--dropdown-item").toHaveCount(1);
    await click(".o-autocomplete--dropdown-item:contains('Patrick')");
    await animationFrame();
    await click(".o_records_selector_popover .btn-primary");
    await animationFrame();
    expect("div.o_ai_prompt").toHaveText("Hello Bob Patrick");
    // clicking on the record should reopen the field selector
    await click("div.o_ai_prompt .o_ai_record");
    await animationFrame();
    expect(".o_records_selector_popover").toHaveCount(1);
    await click(document.body);
    expect.verifySteps([
        'change <p>Hello <span class="o_ai_record" data-oe-protected="true"><span class="d-none">{1:</span><span>Bob</span><span class="d-none">}</span></span> <span class="o_ai_record" data-oe-protected="true"><span class="d-none">{2:</span><span>Patrick</span><span class="d-none">}</span></span> </p>',
    ]);
});
