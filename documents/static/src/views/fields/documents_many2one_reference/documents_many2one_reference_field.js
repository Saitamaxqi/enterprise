import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { Many2OneReferenceField } from "@web/views/fields/many2one_reference/many2one_reference_field";
import { extractM2OFieldProps } from "@web/views/fields/many2one/many2one_field";

/**
 * Hide linked record when it is itself.
 * TODO: clean when documents are no longer linked to themselves.
 */
export class DocumentsMany2OneReferenceField extends Many2OneReferenceField {
    static template = "web.Many2OneReferenceField";

    get m2oProps() {
        const props = super.m2oProps;
        if (this.props.record.data.res_model === "documents.document") {
            props.value = false;
        }
        return props;
    }
}

registry.category("fields").add("documents_many2one_reference", {
    component: DocumentsMany2OneReferenceField,
    displayName: _t("DocumentsMany2OneReference"),
    extractProps(staticInfo, dynamicInfo) {
        return extractM2OFieldProps(staticInfo, dynamicInfo);
    },
    relatedFields: [{ name: "display_name", type: "char" }],
    supportedTypes: ["many2one_reference"],
});
