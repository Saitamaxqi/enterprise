import { registry } from "@web/core/registry";
import { DateTimeField, dateTimeField } from "@web/views/fields/datetime/datetime_field";
import {
    listDateTimeField,
    ListDateTimeField,
} from "@web/views/fields/datetime/list_datetime_field";

export class EsgDateTimeField extends DateTimeField {
    static template = "esg.EsgDateTimeField";

    shouldShowSeparator() {
        return !this.isEmpty(this.endDateField) && super.shouldShowSeparator();
    }
}

export const esgDateRangeField = {
    ...dateTimeField,
    component: EsgDateTimeField,
};

registry.category("fields").add("esg_daterange", esgDateRangeField);

export class EsgListDateTimeField extends ListDateTimeField {
    static template = "esg.EsgDateTimeField";

    shouldShowSeparator() {
        return !this.isEmpty(this.endDateField) && super.shouldShowSeparator();
    }
}

export const esgListDateRangeField = {
    ...listDateTimeField,
    component: EsgListDateTimeField,
};

registry.category("fields").add("esg_list_daterange", esgListDateRangeField);
