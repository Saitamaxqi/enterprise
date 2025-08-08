import { GanttPopover } from "@web_gantt/gantt_popover";


export class AppointmentGanttPopover extends GanttPopover {
    setup() {
        super.setup();
        this.displayPopoverHeader = true;
    }
}
