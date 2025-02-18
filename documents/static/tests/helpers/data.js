import { fields, models, serverState } from "@web/../tests/web_test_helpers";

export class DocumentsDocument extends models.Model {
    _name = "documents.document";

    id = fields.Integer({ string: "ID" });
    name = fields.Char({ string: "Name" });
    thumbnail = fields.Binary({ string: "Thumbnail" });
    favorited_ids = fields.Many2many({ string: "Name", relation: "res.users" });
    is_favorited = fields.Boolean({ string: "Name" });
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
    type = fields.Selection({ string: "Type", selection: [["binary", "File", "folder"]] });
    url = fields.Char({ string: "URL" });
    url_preview_image = fields.Char({ string: "URL preview image" });
    file_size = fields.Integer({ string: "File size" });
    raw = fields.Char({ string: "Raw" });
    access_token = fields.Char({ string: "Access token" });
    available_embedded_actions_ids = fields.Many2many({
        string: "Available Actions",
        // relation: "ir.actions.server",
        relation: "res.partner",
    });
    alias_id = fields.Many2one({ relation: "mail.alias" });
    alias_domain_id = fields.Many2one({ relation: "mail.alias.domain" });
    alias_name = fields.Char({ string: "Alias name" });
    alias_tag_ids = fields.Many2many({ relation: "documents.tag" });
    create_activity_type_id = fields.Many2one({ relation: "mail.activity.type" });
    create_activity_user_id = fields.Many2one({ relation: "res.users" });
    description = fields.Char({ string: "Attachment description" });
    last_access_date_group = fields.Selection({
        string: "Last Accessed On",
        selection: [["0_older", "1_mont", "2_week", "3_day"]],
    });

    get_deletion_delay() {
        return 30;
    }

    get_document_max_upload_limit() {
        return 67000000;
    }

    /**
     * @override
     */
    search_panel_select_range(fieldName) {
        const result = super.search_panel_select_range(...arguments);
        if (fieldName === "folder_id") {
            const coModel = this.env[this._fields[fieldName].relation];
            for (const recordValues of result.values || []) {
                const [record] = coModel.browse(recordValues.id);
                for (const fName of [
                    "display_name",
                    "description",
                    "parent_folder_id",
                    "user_permission",
                    "company_id",
                ]) {
                    recordValues[fName] ??= record[fName];
                }
            }
        }
        return result;
    }

    _records = [
        {
            id: 1,
            name: "Workspace1",
            description: "Workspace",
            folder_id: false,
            available_embedded_actions_ids: [],
            type: "folder",
            access_token: "accessTokenWorkspace1",
        },
    ]
}

export class DocumentsTag extends models.Model {
    _name = "documents.tag";
}

export class MailActivityType extends models.Model {
    _name = "mail.activity.type";

    name = fields.Char({ string: "Activity Type" });
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
                    {
                        id: 1,
                        name: "Workspace1",
                        type: "folder",
                        available_embedded_actions_ids: [],
                        owner_id: false,
                        access_token: "accessTokenWorkspace1"
                    },
                    ...additionalRecords,
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
        owner_id: {
            id: serverState.userId,
            partner_id: {
                id: serverState.partner_id,
                mail: "user@mock.example.com",
                name: "User Mock",
                user_id: serverState.userId,
                partner_share: false,
            },
        },
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
    MailActivityType,
    MailAlias,
    MailAliasDomain,
    DocumentsDocument,
    DocumentsTag,
}
