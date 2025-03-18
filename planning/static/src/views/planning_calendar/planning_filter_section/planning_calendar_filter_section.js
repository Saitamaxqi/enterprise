import { CalendarFilterSection } from "@web/views/calendar/calendar_filter_section/calendar_filter_section";

export class PlanningCalendarFilterSection extends CalendarFilterSection {
    static subTemplates = {
        filter: "planning.PlanningCalendarFilterSection.filter",
    };

    getNoColor(filter) {
        return this.section.fieldName == 'resource_id' ? 'no_filter_color' : '';
    }
}
