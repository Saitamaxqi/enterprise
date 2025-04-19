import { patch } from "@web/core/utils/patch";
import { Record } from "@web/model/relational_model/record";

patch(Record.prototype, {
    computeAiField(fieldName) {
        return this.model.mutex.exec(() => this._computeAiField(fieldName));
    },

    computeAiProperty(fullName) {
        return this.model.mutex.exec(() => this._computeAiProperty(fullName));
    },

    async _computeAiField(fieldName) {
        const field = this.fields[fieldName];
        if (!field?.ai) {
            throw new Error("Cannot compute a non-AI field using AI");
        }
        const value = await this.model.orm.call(this.resModel, "get_ai_field_value", [
            this.resId || [],
            fieldName,
            this._getChanges(),
        ]);
        if (!value) {
            return false;
        }
        // allows to use the "SET" command
        if (field.type === "many2many") {
            await this._update({ [fieldName]: value });
            return true;
        }
        await this._update(
            this._parseServerValues({ [fieldName]: value }, { currentValues: this.data }),
        );
        return true;
    },

    async _computeAiProperty(fullName) {
        const property = this.fields[fullName];
        if (!property?.ai) {
            throw new Error("Cannot compute a non-AI property using AI");
        }
        return await this.model.orm.call(this.resModel, "get_ai_property_value", [
            this.resId || [],
            fullName,
            this._getChanges(),
        ]);
    },
});
