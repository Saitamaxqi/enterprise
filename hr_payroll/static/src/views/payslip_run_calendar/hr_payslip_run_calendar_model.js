import {CalendarModel} from "@web/views/calendar/calendar_model";


export class PayRunCalendarModel extends CalendarModel {

    getColorFromState(state) {
        const colorMap = {
            draft: "#17a2b8",
            verify: "#ffac00",
            close: "#28a745",
            paid: "#71639e",
        };
        return colorMap[state] || null;
    }

    normalizeRecord(rawRecord) {
        const res = super.normalizeRecord(rawRecord);
        res.colorIndex = this.getColorFromState(res.colorIndex?.match(/^\d+_(.+)$/)?.[1] ?? null);
        return res;
    }
}
