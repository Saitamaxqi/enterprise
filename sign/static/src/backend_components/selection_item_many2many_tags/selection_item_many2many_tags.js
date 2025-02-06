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
            tags: this.tags.map(tag => ({
                ...tag,
                text: tag.text,
                updated: false,
            })),
        });
        onWillUpdateProps(() => {
            this.state.tags = this.getTags();
        });
        this.onSave = this.onSave.bind(this);
        this.onDelete = this.onDelete.bind(this);
    }

    getTagsToTextArea() {
        if (this.state.tags.length > 0)
            return this.state.tags.map(tag => tag.text).join("\n") + "\n";
        return "";
    }

    async onKeyUpSelection(ev, value) {
        if (ev.keyCode === 13)
            this.onChangeSelection(ev, value);
    }

    async onChangeSelection(ev, value) {
        // Process tags from input value.
        const tags = value.split('\n').map(tag => tag.trim()).filter(tag => tag);
        const newTags = tags.filter(tag => !this.state.tags.find(existingTag => existingTag.text === tag));

        // Handle removed tags.
        const removedTags = this.state.tags.filter(existingTag => !tags.includes(existingTag.text));
        if (removedTags.length)
            removedTags.forEach(tag => this.onDelete(tag.resId));

        // Handle new tags.
        if (newTags.length) {
            for (const tag of newTags) {
                const resId = await this.searchOrCreateOption(tag);
                this.state.tags = [...this.state.tags, { resId, text: tag, updated: true }];
                this.props.state_popover.option_ids.push(resId);
                this.props.selectionTag.isSelectionItemRendered = true;
                this.onSave();
            }
        }
    }

    async searchOrCreateOption(optionText) {
        const res = await this.orm.searchRead('sign.item.option', [["value", "=", optionText]], ["id"]);
        let resId = res && res.length > 0 ? res[0].id : null;

        if (!resId) {
            const created = await this.orm.create('sign.item.option', [{ value: optionText }]);
            resId = created && created.length > 0 ? created[0] : null;
        }

        return resId;
    }

    getTags() {
        return this.props.record.data[this.props.name]?.records.map((record) =>
            this.getTagProps(record)
        );
    }

    onSave = async () => {
        for (const tag of this.state.tags.filter((tag) => tag.updated)) {
            /* Before saving the tag text, we search if it is previously created in the DB.
            If it is, we re-assign the resId value of the current, otherwise we create a new option.
            This certifies that we'll respect the no duplicates constraint in the database. */
            await this.searchOrCreateOption(tag.text).then((newResId) => {
                const oldPos = this.props.state_popover.option_ids.indexOf(tag.resId);
                this.props.state_popover.option_ids.splice(oldPos, 1, newResId);
                this.props.selectionTag.isSelectionItemRendered = true;
                tag.resId = newResId;
                tag.updated = false;
                this.props.updateSelectionOptions(this.props.state_popover.option_ids);
            });
        }
    };

    onDelete(tagId) {
        this.state.tags = this.state.tags.filter((tag) => tag.resId !== tagId);
        const index = this.props.state_popover.option_ids.indexOf(tagId);
        this.props.state_popover.option_ids.splice(index, 1);
        this.props.selectionTag.isSelectionItemRendered = true;
        this.props.updateSelectionOptions(this.props.state_popover.option_ids);
    }
}
