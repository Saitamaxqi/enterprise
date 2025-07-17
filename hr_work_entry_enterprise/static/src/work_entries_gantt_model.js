import { localStartOf } from "@web_gantt/gantt_helpers";
import { GanttModel } from "@web_gantt/gantt_model";
import { serializeDate } from "@web/core/l10n/dates";

export class WorkEntriesGanttModel extends GanttModel {
    /**
     * @override
     */
    setup() {
        super.setup(...arguments);
    }

    getRange() {
        const { globalStart, globalStop } = this._buildMetaData();
        return { start: globalStart, end: globalStop.minus({ millisecond: 1 }) };
    }

    getRangeFromDate(rangeId, date) {
        const startDate = localStartOf(date, rangeId);
        const stopDate = startDate.plus({ [rangeId]: 1 }).minus({ day: 1 });
        return { focusDate: date, startDate, stopDate, rangeId };
    }

    async resetWorkEntries(cellsInfo, recordIds) {
        const cellsFormattedData = new Set();
        for (const { start, stop, rowId } of cellsInfo) {
            const schedule = this.getSchedule({ start, stop, rowId });
            cellsFormattedData.add({ date: schedule.date, employee_id: schedule.employee_id });
        }
        await this.orm.call("hr.work.entry.regeneration.wizard", "regenerate_work_entries", [
            [],
            [...cellsFormattedData],
            recordIds,
        ]);
        await this.fetchData();
    }

    async multiReplaceRecords(multiCreateData, cellsInfo, records) {
        if (!cellsInfo.length) {
            return;
        }
        const new_records = [];
        const values = await multiCreateData.record.getChanges();
        for (const { start, stop, rowId } of cellsInfo) {
            const schedule = this.getSchedule({ start, stop, rowId });
            new_records.push({ ...schedule, ...values });
        }
        const created = await this.orm.create(this.metaData.resModel, new_records, {
            context: { ...this.searchParams.context, multi_create: true },
        });
        if (records.length && created) {
            await this.orm.unlink(this.metaData.resModel, records);
        }
        await this.fetchData();
    }

    /**
     * @protected
     * @override
     */
    _getDomain(metaData) {
        return this.searchParams.domain;
    }

    /**
     * @protected
     * @override
     */
    async _fetchData(metaData, additionalContext) {
        if (!this.orm.isSample) {
            const { start, end } = this.getRange();
            await this.orm.call("hr.employee", "generate_work_entries", [
                [],
                serializeDate(start),
                serializeDate(end),
            ]);
        }
        await super._fetchData(...arguments);
    }
}
