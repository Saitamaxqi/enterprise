import { SocialPostFormatterMixin } from "./social_post_formatter_mixin";

import { markup } from "@odoo/owl";

import { HtmlField, htmlField } from "@web_editor/js/backend/html_field";
import { registry } from "@web/core/registry";
import { setElementContent } from "@web/core/utils/html";

export class FieldPostPreview extends SocialPostFormatterMixin(HtmlField) {
    static props = {
        ...FieldPostPreview.props,
        mediaType: { type: String, optional: true },
    };

    get markupValue() {
        const $html = $(this.props.record.data[this.props.name] + "");
        $html.find(".o_social_preview_message").each((index, previewMessage) => {
            setElementContent(previewMessage, this._formatPost(previewMessage.textContent.trim()));
        });
        return markup($html[0]?.outerHTML || "");
    }
}

export const fieldPostPreview = {
    ...htmlField,
    component: FieldPostPreview,
    extractProps({ attrs }) {
        const props = htmlField.extractProps(...arguments);
        props.mediaType = attrs.media_type || "";
        return props;
    },
};

registry.category("fields").add("social_post_preview", fieldPostPreview);
