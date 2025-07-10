/* global posmodel */

import { localization } from "@web/core/l10n/localization";
import { useState, onMounted } from "@odoo/owl";
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { DateTimePickerPopover } from "@web/core/datetime/datetime_picker_popover";
import { usePopover } from "@web/core/popover/popover_hook";
import { Domain } from "@web/core/domain";

const { DateTime } = luxon;

export class PosKanbanController extends KanbanController {
    static template = "pos_restaurant_appointment.KanbanController";

    setup() {
        super.setup(...arguments);
        this.popover = usePopover(DateTimePickerPopover, { position: "bottom" });
        this.state = useState({
            date: DateTime.now(),
        });
        this.model = this.env.model;
        this.localization = localization;
        onMounted(async () => {
            await this.createStartFilter(this.state.date);
        });
    }

    async createStartFilter(date) {
        const searchModel = this.model.env.searchModel;
        const kanbanDateFilter = Object.values(searchModel.searchItems).find(
            (si) => si.name === "kanban_date_filter"
        );
        const startIsDomain = Domain.and([
            new Domain([
                [
                    "start",
                    ">",
                    `${date
                        .set({ hour: 0, minute: 0, second: 0 })
                        .toUTC()
                        .toFormat("yyyy-MM-dd HH:mm:ss", {
                            numberingSystem: "latn",
                        })}`,
                ],
            ]),
            new Domain([
                [
                    "start",
                    "<=",
                    `${date
                        .set({ hour: 23, minute: 59, second: 59 })
                        .toUTC()
                        .toFormat("yyyy-MM-dd HH:mm:ss", {
                            numberingSystem: "latn",
                        })}`,
                ],
            ]),
        ]);
        if (kanbanDateFilter) {
            kanbanDateFilter.domain = startIsDomain.toString();
            kanbanDateFilter.description = `Start is ${date.toFormat(
                this.localization.dateFormat
            )}`;
            searchModel._notify();
            if (!searchModel.query.some((sm) => sm.searchItemId === kanbanDateFilter.id)) {
                searchModel.toggleSearchItem(kanbanDateFilter.id);
            }
        } else {
            searchModel.createNewFilters([
                {
                    description: `Start is ${date.toFormat(this.localization.dateFormat)}`,
                    domain: startIsDomain.toString(),
                    invisible: "True",
                    type: "filter",
                    name: "kanban_date_filter",
                },
            ]);
        }
    }

    onClickDateBtn(ev) {
        this.popover.open(ev.currentTarget, {
            pickerProps: {
                onSelect: async (value) => {
                    if (value) {
                        this.state.date = value;
                        await this.createStartFilter(value);
                    } else {
                        this.onRemove();
                    }
                    this.popover.close();
                },
                type: "date",
                value: this.state.date,
            },
        });
    }

    get totalPersonCount() {
        return this.model.root.groups.reduce((groupSum, group) => {
            const groupTotal = group.list.records.reduce(
                (recordSum, record) => recordSum + record.data.waiting_list_capacity,
                0
            );
            return groupSum + groupTotal;
        }, 0);
    }

    async createRecord() {
        const action = await this.env.model.orm.call(
            "calendar.event",
            "action_create_booking_form_view",
            [false, posmodel.config.raw.appointment_type_id]
        );
        return this.env.model.action.doAction(action, {
            onClose: async () => {
                const root = this.env.model.root;
                const { limit, offset } = root;
                await root.load({ offset, limit });
            },
        });
    }
}
