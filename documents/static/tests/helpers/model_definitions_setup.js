import {
    addFakeModel,
    addModelNamesToFetch,
} from "@bus/../tests/helpers/model_definitions_helpers";

addModelNamesToFetch([
    'documents.document', 'documents.tag', 'ir.actions.server', 'ir.embedded.actions',
]);

addFakeModel("res.fake", {
    email_cc: { type: "char" },
    phone: { type: "char" },
    partner_ids: { relation: "res.partner", string: "Related partners", type: "one2many" },
});
