import { Component, useExternalListener, useRef, useState } from "@odoo/owl";

import { useAutofocus, useService } from "@web/core/utils/hooks";

export class TimesheetTimerHeaderButtons extends Component {
    static template = "timesheet_grid.TimesheetTimerHeaderButtons";
    static props = {
        startTimer: { type: Function, optional: true },
        stopTimer: { type: Function, optional: true },
        deleteTimer: { type: Function, optional: true },
        timerRunning: { type: Boolean, optional: true },
    };

    setup() {
        this.resModel = "account.analytic.line";
        this.timerService = useService("timesheet_timer");
        this.timerReactive = useState(this.timerService.timer);
        this.startButton = useRef("startButton");
        this.stopButton = useRef("stopButton");
        useAutofocus({ refName: "startButton" });
        useAutofocus({ refName: "stopButton" });
        useExternalListener(document.body, "click", (ev) => {
            if (
                ev.target.closest(".modal, .popover") ||
                ["input", "textarea"].includes(ev.target.tagName.toLowerCase())
            ) {
                return;
            }
            this.startButton.el ? this.startButton.el.focus() : this.stopButton.el.focus();
        });
    }

    async _onClickStartTimer() {
        if (this.props.startTimer) {
            this.props.startTimer();
        } else {
            this.timerService.startTimer();
        }
    }

    async _onClickStopTimer() {
        if (this.props.stopTimer) {
            await this.props.stopTimer();
        } else {
            await this.timerService.stopTimer();
        }
    }

    async _onClickDeleteTimer() {
        if (this.props.deleteTimer) {
            this.props.deleteTimer();
        } else {
            this.timerService.deleteTimer();
        }
    }
}
