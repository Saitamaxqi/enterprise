import { WorkEntryCalendarMultiSelectionButtons } from "@hr_work_entry/views/work_entry_calendar/work_entry_multi_selection_buttons";

export class WorkEntriesMultiSelectionButtons extends WorkEntryCalendarMultiSelectionButtons {
    /**
     * @override
     */
    createFakeMultiCreateData(workEntryType) {
        const multiCreateData = super.createFakeMultiCreateData(workEntryType);
        delete multiCreateData.record.data.employee_id;
        delete multiCreateData.record.fields.employee_id;
        return multiCreateData;
    }
}
