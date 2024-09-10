import { onWillStart, useState } from "@odoo/owl";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { CalendarCommonPopover } from "@web/views/calendar/calendar_common/calendar_common_popover";
import { formatFloatTime } from "@web/views/fields/formatters";
import { formatFloat } from "@web/core/utils/numbers";
import { AddressRecurrencyConfirmationDialog } from "@planning/components/address_recurrency_confirmation_dialog/address_recurrency_confirmation_dialog";
import { usePlanningRecurringDeleteAction } from "../../planning_hooks";

export class PlanningCalendarCommonPopover extends CalendarCommonPopover {
    static subTemplates = {
        ...CalendarCommonPopover.subTemplates,
        body: "planning.PlanningCalendarCommonPopover.body",
    };
    setup() {
        super.setup(...arguments);
        this.dialogService = useService("dialog");
        this.orm = useService("orm");
        this.state = useState({
            recurrenceUpdate: "this",
        });
        this.planningRecurrenceDeletion = usePlanningRecurringDeleteAction();
        onWillStart(this.onWillStart);
    }

    async onWillStart() {
        this.isManager = await user.hasGroup("planning.group_planning_manager");
    }

    onDeleteEvent() {
        const record = this.props.record.rawRecord;
        if (record.repeat) {
            this.dialogService.add(AddressRecurrencyConfirmationDialog, {
                confirm: async () => {
                    await this.planningRecurrenceDeletion._actionAddressRecurrency(
                        { resId: record.id, resModel: this.props.model  .resModel },
                        this.state.recurrenceUpdate
                    );
                    this.props.model.unlinkRecord(record.id);
                    this.props.close();
                },
                onChangeRecurrenceUpdate: this.planningRecurrenceDeletion._setRecurrenceUpdate.bind(this),
                selected: this.state.recurrenceUpdate,
            });
        } else {
            super.onDeleteEvent();
        }
    }

    get isEventEditable() {
        return this.isManager && super.isEventEditable;
    }

    get data() {
        return this.props.record.rawRecord;
    }

    get allocatedHoursFormatted() {
        return this.data.allocated_hours && formatFloatTime(this.data.allocated_hours);
    }

    get allocatedPercentageFormatted() {
        return this.data.allocated_percentage && formatFloat(this.data.allocated_percentage);
    }

    /**
     * @override
     */
    get hasFooter() {
        return this.isManager && super.hasFooter;
    }

    isSet(fieldName) {
        return this.data[fieldName];
    }
}
