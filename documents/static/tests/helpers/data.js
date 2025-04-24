import { mailModels } from "@mail/../tests/mail_test_helpers";
import { fields, models, serverState, webModels } from "@web/../tests/web_test_helpers";

export class DocumentsDocument extends models.Model {
    _name = "documents.document";
    _parent_name = "folder_id";

    id = fields.Integer({ string: "ID" });
    name = fields.Char({ string: "Name" });
    thumbnail = fields.Binary({ string: "Thumbnail" });
    favorited_ids = fields.Many2many({ string: "Name", relation: "res.users" });
    is_favorited = fields.Boolean({ string: "Name" });
    is_folder = fields.Boolean({ string: "is_folder" }); // used for ordering
    is_multipage = fields.Boolean({ string: "Is multipage" });
    is_company_root_folder = fields.Boolean({ string: "Pinned to Company roots" });
    mimetype = fields.Char({ string: "Mimetype" });
    partner_id = fields.Many2one({ string: "Related partner", relation: "res.partner" });
    owner_id = fields.Many2one({ string: "Owner", relation: "res.users" });
    previous_attachment_ids = fields.Many2many({
        string: "History",
        relation: "ir.attachment",
    });
    tag_ids = fields.Many2many({ string: "Tags", relation: "documents.tag" });
    folder_id = fields.Many2one({ string: "Folder", relation: "documents.document" });
    res_model = fields.Char({ string: "Model (technical)" });
    attachment_id = fields.Many2one({ relation: "ir.attachment" });
    company_id = fields.Many2one({ string: "Company", relation: "res.company" });
    active = fields.Boolean({ default: true, string: "Active" });
    activity_ids = fields.One2many({ relation: "mail.activity" });
    checksum = fields.Char({ string: "Checksum" });
    file_extension = fields.Char({ string: "File extension" });
    thumbnail_status = fields.Selection({
        string: "Thumbnail status",
        selection: [["none", "None"]],
    });
    lock_uid = fields.Many2one({ relation: "res.users" });
    message_attachment_count = fields.Integer({ string: "Message attachment count" });
    message_follower_ids = fields.One2many({ relation: "mail.followers" });
    message_ids = fields.One2many({ relation: "mail.message" });
    res_id = fields.Integer({ string: "Resource ID" });
    res_name = fields.Char({ string: "Resource Name" });
    res_model_name = fields.Char({ string: "Resource Model Name" });
    type = fields.Selection({
        string: "Type",
        selection: [
            ["binary", "File"],
            ["url", "Url"],
            ["folder", "Folder"],
        ],
        default: "binary",
    });
    url = fields.Char({ string: "URL" });
    url_preview_image = fields.Char({ string: "URL preview image" });
    file_size = fields.Integer({ string: "File size" });
    raw = fields.Char({ string: "Raw" });
    access_token = fields.Char({ string: "Access token" });
    user_permission = fields.Selection({
        string: "User Permission",
        selection: [
            ["edit", "Editor"],
            ["view", "Viewer"],
            ["none", "None"],
        ],
        default: "edit",
    });
    available_embedded_actions_ids = fields.Many2many({
        string: "Available Actions",
        relation: "ir.embedded.actions",
    });
    alias_id = fields.Many2one({ relation: "mail.alias" });
    alias_domain_id = fields.Many2one({ relation: "mail.alias.domain" });
    alias_name = fields.Char({ string: "Alias name" });
    alias_tag_ids = fields.Many2many({ relation: "documents.tag" });
    mail_alias_domain_count = fields.Integer();
    create_activity_type_id = fields.Many2one({ relation: "mail.activity.type" });
    create_activity_user_id = fields.Many2one({ relation: "res.users" });
    description = fields.Char({ string: "Attachment description" });
    last_access_date_group = fields.Selection({
        string: "Last Accessed On",
        selection: [
            ["0_older", "Older"],
            ["1_month", "This Month"],
            ["2_week", "This Week"],
            ["3_day", "Today"],
        ],
        default: "3_day",
    });

    get_deletion_delay() {
        return 30;
    }

    get_document_max_upload_limit() {
        return 67000000;
    }

    get_details_panel_res_models() {
        return ["res.partner"];
    }

    action_create_shortcut() {
        return;
    }

    action_move_documents(recordIds, folderId) {
        const records = this.filter((r) => recordIds.includes(r.id));
        for (const record of records) {
            record.folder_id = folderId;
        }
    }

    /**
     * @override to avoid super() not working for us.
     */
    search_panel_select_range(fieldName) {
        const result = super.search_panel_select_range(...arguments);
        result.values = [
            {
                bold: true,
                childrenIds: [],
                parentId: false,
                user_permission: "view",
                display_name: "Company",
                id: "COMPANY",
                description: "Common roots for all company users.",
            },
            {
                bold: true,
                childrenIds: [],
                parentId: false,
                user_permission: "edit",
                display_name: "My Drive",
                id: "MY",
                description: "Your individual space.",
            },
            {
                bold: true,
                childrenIds: [],
                parentId: false,
                user_permission: "edit",
                display_name: "Shared with me",
                id: "SHARED",
                description: "Additional documents you have access to.",
            },
            {
                bold: true,
                childrenIds: [],
                parentId: false,
                user_permission: "edit",
                display_name: "Recent",
                id: "RECENT",
                description: "Recently accessed documents.",
            },
            {
                bold: true,
                childrenIds: [],
                parentId: false,
                user_permission: "edit",
                display_name: "Trash",
                id: "TRASH",
                description: "Items in trash will be deleted forever after 30 days.",
            },
            ...this.env["documents.document"]
                .search_read([["type", "=", "folder"]])
                .filter((r) => r.type === "folder")
                .map((record) => {
                    const recordValues = {};
                    if (!record.folder_id) {
                        recordValues.folder_id = !record.owner_id
                            ? "COMPANY"
                            : record.owner_id[0] === serverState.userId
                            ? "MY"
                            : "SHARED";
                    } else {
                        recordValues.folder_id = record.folder_id[0];
                    }
                    if (!record.active) {
                        recordValues.folder_id = "TRASH";
                    }
                    if (record.alias_tag_ids) {
                        recordValues.alias_tag_ids = record.alias_tag_ids.map((id) => {
                            const tag = this.env["documents.tag"].search_read([["id", "=", id]])[0];
                            return { id, color: tag.color, display_name: tag.name };
                        });
                    }
                    [
                        "alias_domain_id",
                        "alias_name",
                        "mail_alias_domain_count",
                        "company_id",
                        "create_activity_type_id",
                        "owner_id",
                        "partner_id",
                        "description",
                        "display_name",
                        "id",
                        "is_folder",
                        "type",
                        "user_permission",
                    ].forEach((fieldName) => (recordValues[fieldName] = record[fieldName]));
                    return recordValues;
                }),
        ];
        return result;
    }
}

export class DocumentsTag extends models.Model {
    _name = "documents.tag";

    name = fields.Char({ string: "Tag Name" });
    color = fields.Integer({ default: 1 });
}

export class IrEmbeddedActions extends models.Model {
    _name = "ir.embedded.actions";

    name = fields.Char({ string: "Action Name" });
}

export class MailAlias extends models.Model {
    _name = "mail.alias";

    alias_name = fields.Char({ string: "Alias Name" });
}

export class MailAliasDomain extends models.Model {
    _name = "mail.alias.domain";

    name = fields.Char({ string: "Alias Domain Name" });
}

/**
 * @param {Number} id
 * @param {String} name
 * @param {object?} data
 * @return {{}}
 */
export function makeDocumentRecordData(id, name, data = {}) {
    const strippedName = name.replace(/\s/g, "");
    const defaultValues = {
        available_embedded_actions_ids: [],
        folder_id: false,
        company_id: false,
        owner_id: false,
        partner_id: false,
        type: "binary",
    };
    const documentType = data.type || defaultValues.type;
    return {
        ...defaultValues,
        id: id,
        access_token: `accessToken${strippedName}`,
        is_folder: documentType === "folder",
        name: name,
        type: documentType,
        ...data,
    };
}

/**
 * @returns {Object}
 */
export function getDocumentsTestServerData(additionalRecords = []) {
    return {
        models: {
            "res.users": {
                records: [
                    { name: "OdooBot", id: serverState.odoobotId },
                    {
                        name: serverState.partnerName,
                        id: serverState.userId,
                        active: true,
                        partner_id: serverState.partnerId,
                    },
                ],
            },
            "documents.document": {
                records: [
                    makeDocumentRecordData(1, "Folder 1", { type: "folder" }),
                    ...additionalRecords,
                ],
            },
            "documents.tag": {
                records: [
                    {
                        id: 1,
                        name: "Colorless",
                        color: 0,
                    },
                    {
                        id: 2,
                        name: "Colorful",
                        color: 1,
                    },
                ],
            },
            "mail.alias": {
                records: [{ id: 1, alias_name: "alias" }],
            },
            "mail.alias.domain": {
                records: [
                    { id: 1, name: "odoo.com" },
                    { id: 2, name: "runbot.odoo.com" },
                ],
            },
        },
    };
}

export function getBasicPermissionPanelData(recordExtra) {
    const record = {
        access_internal: "view",
        access_via_link: "view",
        access_ids: [],
        active: true,
        owner_id: false,
        user_permission: "view",
        ...recordExtra,
    };
    const selections = {
        access_via_link: [
            ["view", "Viewer"],
            ["edit", "Editor"],
            ["none", "None"],
        ],
        access_via_link_options: [
            ["1", "Must have the link to access"],
            ["0", "Discoverable"],
        ],
        access_internal: [
            ["view", "Viewer"],
            ["edit", "Editor"],
            ["none", "None"],
        ],
        doc_access_roles: [
            ["view", "Viewer"],
            ["edit", "Editor"],
        ],
    };
    return { record, selections };
}

export const DocumentsModels = {
    ...mailModels,
    IrEmbeddedActions,
    MailAlias,
    MailAliasDomain,
    ResCompany: webModels.ResCompany,
    DocumentsDocument,
    DocumentsTag,
};

export function getDocumentsModel(modelName) {
    return Object.values(DocumentsModels).find((model) => model._name === modelName);
}
