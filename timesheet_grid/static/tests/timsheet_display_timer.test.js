import { test, expect } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";
import { EventBus } from "@odoo/owl";
import { serializeDateTime } from "@web/core/l10n/dates";
import { mountWithCleanup, onRpc } from "@web/../tests/web_test_helpers";

import { defineTimesheetModels } from "./hr_timesheet_models";
import { TimesheetDisplayTimer, TimesheetTimerFloatTimerField } from "@timesheet_grid/components/timesheet_display_timer/timesheet_display_timer";

const now = luxon.DateTime.utc();
defineTimesheetModels();
async function mountFloatTimerField(timerRunning) {
    await mountWithCleanup(TimesheetTimerFloatTimerField, {
        props: {
            value: 12 + 34 / 60 + (56 * timerRunning / 3600),
            timerRunning,
            record: {
                isInvalid: () => false,
                model: { bus: new EventBus() },
                isFieldInvalid: () => {},
            },
            displayRed: false,
        },
    });
}

test("TimesheetTimerFloatTimerField should display seconds when timerRunning is true", async () =>  {
    await mountFloatTimerField(true);
    expect("input.o_input").toHaveValue("12:34:56", {
        message: `TimesheetTimerFloatTimerField should display seconds when the timer is running.`,
    });
});

test("TimesheetTimerFloatTimerField should not display seconds when timerRunning is false", async () => {
    await mountFloatTimerField(false);
    expect("input.o_input").toHaveValue("12:34", {
        message: `TimesheetTimerFloatTimerField should not display seconds when the timer is not running.`,
    });
});

onRpc(({ method }) => {
    if (method === "get_server_time") {
        return Promise.resolve(serializeDateTime(now));
    }
})

async function _testTimesheetDisplayTimer(timerStart, timerPause) {
    const expectedRunning = !!timerStart && !timerPause;
    await mountWithCleanup(TimesheetDisplayTimer, {
        props: {
            name: "plop",
            record: {
                resModel: "dummy",
                isInvalid: () => false,
                model: { bus: new EventBus() },
                data: {
                    timer_start: timerStart,
                    timer_pause: timerPause,
                    plop: 1,
                },
                isFieldInvalid: () => {},
            },
        },
    });
    const timerStartInput = queryOne("input");
    const originalValue = timerStartInput.value;
    await new Promise((resolve) => setTimeout(resolve, 2000));
    const currentValue = timerStartInput.value;

    let matcher = expect(originalValue);
    matcher = expectedRunning ? matcher.not : matcher;
    matcher.toBe(currentValue, {
        message: `The value should ${"not ".repeat(!expectedRunning)}have been updated after 1 second`
    });
}

test("timesheet_display_timer should update the timer when timer_start is truthy and timer_pause is falsy", async () => {
    await _testTimesheetDisplayTimer(now.minus({ hours: 1 }), false);
});

test("timesheet_display_timer should not update the timer when timer_start is falsy", async () => {
    await _testTimesheetDisplayTimer(false, false);
});

test("timesheet_display_timer should not update the timer when timer_start and timer_pause are truthy", async () => {
    await _testTimesheetDisplayTimer(
        now.minus({ hours: 1 }),
        now.minus({ minutes: 30 }),
    );
});
