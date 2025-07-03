import { beforeEach, expect, test } from "@odoo/hoot";
import { keyDown } from "@odoo/hoot-dom";
import { contains, defineModels, makeMockServer, mountView } from "@web/../tests/web_test_helpers";
import { DocumentsModels } from "./helpers/data";
import { mountDocumentsKanbanView } from "./helpers/views/kanban";
import { getEnrichedSearchArch } from "./helpers/views/search";

defineModels(DocumentsModels);

beforeEach(async () => {
    const { env } = await makeMockServer();

    const resPartnerIds = env["res.partner"].create([
        { name: "Hazard" },
        { name: "Lukaku" },
        { name: "De Bruyne" },
        { email: "raoul@grosbedon.fr", name: "Raoul Grosbedon" },
        { email: "raoulette@grosbedon.fr", name: "Raoulette Grosbedon" },
    ]);
    const resUsersIds = env["res.users"].create([
        {
            name: "Hazard",
            partner_id: resPartnerIds[0],
            login: "hazard",
            password: "hazard",
        },
        { name: "Lukaku", partner_id: resPartnerIds[1] },
        { name: "De Bruyne", partner_id: resPartnerIds[2] },
    ]);
    const documentsFolderIds = env["documents.document"].create([
        {
            name: "Workspace1",
            type: "folder",
            access_internal: "edit",
            user_permission: "edit",
            is_company_root_folder: true,
            folder_id: false,
            owner_id: false,
        },
    ]);
    const documentsTagIds = env["documents.tag"].create([
        { name: "New", sequence: 11 },
        { name: "Draft", sequence: 10 },
        { name: "No stress", sequence: 10 },
    ]);
    const resFakeIds = env["res.fake"].create([{ name: "fake1" }, { name: "fake2" }]);
    const irAttachmentIds = env["ir.attachment"].create([{}, {}]);

    env["documents.document"].create([
        {
            name: "Workspace2",
            type: "folder",
            access_internal: "edit",
            user_permission: "edit",
            is_company_root_folder: true,
            folder_id: false,
            owner_id: false,
        },
        {
            name: "Workspace3",
            folder_id: documentsFolderIds[0],
            type: "folder",
            access_internal: "edit",
            user_permission: "edit",
        },
        {
            activity_state: "today",
            available_embedded_actions_ids: [],
            file_size: 30000,
            folder_id: documentsFolderIds[0],
            is_editable_attachment: true,
            name: "yop",
            owner_id: resUsersIds[0],
            partner_id: resPartnerIds[1],
            res_id: resFakeIds[0],
            res_model: "res.fake",
            res_model_name: "Task",
            res_name: "Write specs",
            tag_ids: [documentsTagIds[0], documentsTagIds[1]],
        },
        {
            attachment_id: irAttachmentIds[1],
            available_embedded_actions_ids: [],
            file_size: 20000,
            folder_id: documentsFolderIds[0],
            mimetype: "application/pdf",
            name: "blip",
            owner_id: resUsersIds[1],
            partner_id: resPartnerIds[1],
            res_id: resFakeIds[1],
            res_model: "res.fake",
            res_model_name: "Task",
            res_name: "Write tests",
            tag_ids: [documentsTagIds[1]],
        },
        {
            available_embedded_actions_ids: [],
            file_size: 15000,
            folder_id: documentsFolderIds[0],
            lock_uid: resUsersIds[2],
            name: "gnap",
            owner_id: resUsersIds[1],
            partner_id: resPartnerIds[0],
            res_id: false,
            res_model: false,
            res_model_name: "Task",
            tag_ids: [documentsTagIds[0], documentsTagIds[1], documentsTagIds[2]],
        },
        {
            available_embedded_actions_ids: [],
            file_size: 10000,
            folder_id: documentsFolderIds[0],
            mimetype: "image/png",
            name: "burp",
            owner_id: resUsersIds[0],
            partner_id: resPartnerIds[2],
            res_id: irAttachmentIds[0],
            res_model: "ir.attachment",
            res_model_name: "Attachment",
        },
        {
            available_embedded_actions_ids: [],
            file_size: 40000,
            folder_id: documentsFolderIds[0],
            lock_uid: resUsersIds[0],
            name: "zip",
            owner_id: resUsersIds[1],
            partner_id: resPartnerIds[1],
            tag_ids: documentsTagIds,
        },
        {
            available_embedded_actions_ids: [],
            file_size: 70000,
            folder_id: documentsFolderIds[1],
            name: "pom",
            owner_id: resUsersIds[0],
            partner_id: resPartnerIds[2],
            res_id: false,
            res_model: false,
            res_model_name: "Document",
        },
        {
            active: false,
            file_size: 70000,
            available_embedded_actions_ids: [],
            folder_id: documentsFolderIds[0],
            name: "wip",
            owner_id: resUsersIds[2],
            partner_id: resPartnerIds[2],
            res_id: irAttachmentIds[0],
            res_model: "ir.attachment",
            res_model_name: "Attachment",
        },
        {
            active: false,
            available_embedded_actions_ids: [],
            file_size: 20000,
            folder_id: documentsFolderIds[0],
            mimetype: "text/plain",
            name: "zorro",
            owner_id: resUsersIds[2],
            partner_id: resPartnerIds[2],
        },
    ]);
});

test("documents list: don't unselect all when interacting with the headers", async () => {
    await mountView({
        type: "list",
        resModel: "documents.document",
        arch: /* xml */ `
            <list js_class="documents_list">
                <field name="type" invisible="1" />
                <field name="name" />
                <field name="partner_id" />
                <field name="owner_id" />
                <field name="type" />
            </list>
        `,
        searchViewArch: getEnrichedSearchArch(),
    });

    await contains(".o_data_row:eq(0) .o_list_record_selector input").click();
    await contains(".o_data_row:eq(1) .o_list_record_selector input").click();

    expect(".o_data_row_selected").toHaveCount(2);

    await contains("th:eq(1) .o_resize", { visible: false }).dragAndDrop("th:eq(2)");

    expect(".o_data_row_selected").toHaveCount(2);
});

test("documents kanban: select a range with SHIFT key", async () => {
    await mountDocumentsKanbanView({
        arch: /* xml */ `
            <kanban js_class="documents_kanban" draggable="true">
                <templates>
                    <t t-name="card" class="flex-row">
                        <i class="fa fa-circle mt-1 o_record_selector" />
                        <field name="name" />
                    </t>
                </templates>
            </kanban>
        `,
    });

    await contains(".o_kanban_record:eq(1)").click();

    expect(".o_kanban_record:eq(1)").toHaveClass("o_record_selected");

    await keyDown("Shift");
    await contains(".o_kanban_record:eq(4)").click();

    expect(".o_record_selected").toHaveCount(4);
});
