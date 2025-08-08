import { GanttPopover } from "@web_gantt/gantt_popover";


export class AppointmentGanttPopover extends GanttPopover {
    static template = "appointment.GanttPopover";
    setup() {
        super.setup();
        this.displayPopoverHeader = true;
    }
}
