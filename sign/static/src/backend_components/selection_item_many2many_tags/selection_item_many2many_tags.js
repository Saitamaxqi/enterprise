/** @odoo-module **/

import { Many2ManyTagsField } from "@web/views/fields/many2many_tags/many2many_tags_field";
import { useService } from "@web/core/utils/hooks";
import { useState, onWillUpdateProps } from "@odoo/owl";

export class SelectionItemMany2ManyTagsField extends Many2ManyTagsField {
    static template = 'sign.SelectionItemMany2ManyTagsField';

    static props = {
        ...Many2ManyTagsField.props,
        selectionTag: { type: Object },
        updateSelectionOptions: { type: Function },
        state_popover: { type: Object },
    };

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.state = useState({
            editingTag: null,
            newText: '',
            originalValue: '',
            tags: this.tags,
        });

        onWillUpdateProps(() => {
            this.state.tags = this.getTags();
        });

        this.onEditTag = this.onEditTag.bind(this);
        this.onSave = this.onSave.bind(this);
        this.onUndo = this.onUndo.bind(this);
    }

    getTags() {
        return this.props.record.data[this.props.name]?.records.map((record) =>
            this.getTagProps(record)
        );
}

    onEditTag(tag) {
        this.state.editingTag = tag;
        this.state.originalValue = tag.text; // Save the original value
        this.state.newText = tag.text; // Set the current value for editing
    }

    onSave = async () => {
        if (this.state.editingTag && this.state.newText) {
            const updatedText = this.state.newText;

            // Update the backend with the edited tag value, then fetch and update the frontend with the latest data.
            this.orm.write("sign.item.option", [this.state.editingTag.resId], { value: updatedText })
                .then(() => {
                    this.props.selectionTag.isSelectionItemEdited = true;
                    this.props.selectionTag.isSelectionItemRendered = true;
                    return this.props.updateSelectionOptions(this.props.state_popover.option_ids);
                })

            // Update the matching tag in the state and reset editing state.
            this.state.tags = this.state.tags.map((tag) =>
                tag.id === this.state.editingTag.id ? { ...tag, text: updatedText, display_name: updatedText } : tag
            );
            this.state.editingTag = null;
            this.state.newText = '';
        } else {
            // Revert to original value if no changes were made.
            this.state.editingTag.text = this.state.originalValue;
            this.state.editingTag = null;
        }
    };

    async deleteTag(id) {
        super.deleteTag(id);
        this.state.tags = this.state.tags.filter((tag) => tag.id !== id);
    }

    onUndo() {
        if (this.state.editingTag) {
            this.state.editingTag.text = this.state.originalValue;
            this.state.editingTag = null;
        }
    }
}
