import { WorkEntryCalendarMultiSelectionButtons } from "@hr_work_entry/views/work_entry_calendar/work_entry_multi_selection_buttons";

export class WorkEntriesMultiSelectionButtons extends WorkEntryCalendarMultiSelectionButtons {
    /**
     * @override
     */
    makeValues(workEntryTypeId) {
        const values = super.makeValues(workEntryTypeId);
        delete values.employee_id;
        return values;
    }
}
