import { CalendarSidePanel } from "@web/views/calendar/calendar_side_panel/calendar_side_panel";
import { PlanningCalendarFilterSection } from "../planning_filter_section/planning_calendar_filter_section";

export class PlanningCalendarSidePanel extends CalendarSidePanel {
    static template = "planning.PlanningCalendarSidePanel";
    static components = {
        ...CalendarSidePanel.components,
        FilterSection: PlanningCalendarFilterSection,
    };
}
