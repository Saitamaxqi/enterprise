import { formatFloatTime } from "@web/views/fields/formatters";
import { WorkEntriesGanttPopover } from "./work_entries_gantt_popover";
import { HrGanttRenderer } from "@hr_gantt/hr_gantt_renderer";
import { _t } from "@web/core/l10n/translation";
import { WorkEntriesMultiSelectionButtons } from "@hr_work_entry_enterprise/work_entries_multi_selection_buttons";
import { onWillRender, onWillStart } from "@odoo/owl";
import { user } from "@web/core/user";
import { Domain } from "@web/core/domain";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
const { DateTime } = luxon;

export class WorkEntriesGanttRenderer extends HrGanttRenderer {
    static pillTemplate = "hr_work_entry_enterprise.WorkEntriesGanttRenderer.Pill";
    static components = {
        ...HrGanttRenderer.components,
        Popover: WorkEntriesGanttPopover,
        MultiSelectionButtons: WorkEntriesMultiSelectionButtons,
    };

    setup() {
        super.setup();
        onWillStart(async () => {
            const { globalStart, globalStop } = this.model.metaData;
            const contracts = await this.orm.formattedReadGroup(
                "hr.version",
                Domain.and([
                    [["contract_date_start", "<", globalStop.toISODate()]],
                    Domain.or([
                        [["contract_date_end", ">", globalStart.toISODate()]],
                        [["contract_date_end", "=", false]],
                    ]),
                ]).toList(),
                ["employee_id", "contract_date_start:day", "contract_date_end:day"],
                []
            );
            this.contractsByEmployee = new Map();
            for (const contract of contracts) {
                const employeeId = contract.employee_id[0];
                if (!this.contractsByEmployee.has(employeeId)) {
                    this.contractsByEmployee.set(employeeId, []);
                }
                this.contractsByEmployee.get(employeeId).push(contract);
            }
        });
        onWillRender(async () => {
            const userFavoritesWorkEntriesIds = await this.orm.formattedReadGroup(
                "hr.work.entry",
                [
                    ["create_uid", "=", user.userId],
                    ["create_date", ">", DateTime.local().minus({ months: 3 }).toISODate()],
                ],
                ["work_entry_type_id", "create_date:day"],
                [],
                {
                    order: "create_date:day desc",
                    limit: 6,
                }
            );
            this.userFavoritesWorkEntries = await this.orm.read(
                "hr.work.entry.type",
                userFavoritesWorkEntriesIds.map((r) => r.work_entry_type_id[0]),
                ["display_name", "display_code", "color"]
            );
            this.userFavoritesWorkEntries = this.userFavoritesWorkEntries.sort((a, b) =>
                a.display_code
                    ? a.display_code.localeCompare(b.display_code)
                    : a.display_name.localeCompare(b.display_name)
            );
        });
    }

    /**
     * @override
     */
    getRowTypeHeight(type) {
        return {
            t0: 24,
            t1: 45,
            t2: 10,
        }[type];
    }

    /**
     * @override
     */
    getDurationStr(record) {
        const durationStr = formatFloatTime(record.duration, {
            noLeadingZeroHour: true,
        }).replace(/(:00|:)/g, "h");
        return `${durationStr}`;
    }

    /**
     * @override
     */
    getDisplayName(pill) {
        const { computePillDisplayName, scale } = this.model.metaData;
        const { id: scaleId } = scale;
        const { record } = pill;

        if (!computePillDisplayName) {
            return record.display_name;
        }

        /** @type {string[]} */
        const labels = [];
        if (scaleId === "month") {
            labels.push(record.display_code);
        } else if (scaleId === "week") {
            labels.push(record.work_entry_type_id.display_name);
        }

        /** @type {string[]} */
        const labelElements = [labels.join(" - ")];

        return labelElements.filter((el) => !!el).join(" ");
    }

    /**
     * @override
     */
    enrichPill(pill) {
        pill = super.enrichPill(pill);
        return {
            ...pill,
            subName: this.getDurationStr(pill.record),
            className: pill.className + " justify-content-center flex-column",
        };
    }

    /**
     * @override
     */
    async getPopoverProps(pill) {
        const record = pill.record;
        const props = await super.getPopoverProps(...arguments);
        const { canEdit } = this.model.metaData;
        props.buttons = [
            ...props.buttons,
            ...(record.duration >= 1
                ? [
                      {
                          id: "action_split",
                          text: _t("Split"),
                          class: "btn btn-sm btn-secondary",
                          onClick: () => {
                              this.model.mutex.exec(async () => {
                                  this.dialogService.add(
                                      FormViewDialog,
                                      {
                                          title: _t("Split Work Entry"),
                                          resModel: "hr.work.entry",
                                          onRecordSave: async (record) => {
                                              await this.orm.call("hr.work.entry", "action_split", [
                                                  props.resId,
                                                  {
                                                      duration: record.data.duration,
                                                      work_entry_type_id:
                                                          record.data.work_entry_type_id.id,
                                                      name: record.data.name,
                                                  },
                                              ]);
                                              return true;
                                          },
                                          context: {
                                              form_view_ref:
                                                  "hr_work_entry.hr_work_entry_calendar_gantt_view_form",
                                              default_duration: props.context.duration / 2,
                                              default_name: props.context.name,
                                              default_work_entry_type_id:
                                                  props.context.work_entry_type_id,
                                              default_employee_id: props.context.employee_id,
                                              default_date: props.context.date,
                                          },
                                          canExpand: false,
                                      },
                                      {
                                          onClose: () => {
                                              this.model.fetchData();
                                          },
                                      }
                                  );
                              });
                          },
                      },
                  ]
                : []),
            ...(canEdit
                ? [
                      {
                          id: "unlink",
                          text: _t("Delete"),
                          class: "btn btn-sm ms-auto btn-danger",
                          onClick: () => {
                              this.model.mutex.exec(async () => {
                                  await this.orm.unlink("hr.work.entry", [props.resId]);
                                  this.model.fetchData();
                              });
                          },
                      },
                  ]
                : []),
        ];
        return {
            ...props,
            title: record.work_entry_type_id.display_name + " - " + this.getDurationStr(record),
            buttons: record.state === "validated" ? null : props.buttons,
        };
    }

    /**
     * @override
     */
    getPill(record) {
        const pill = super.getPill(record);
        const isLocked = record.state === "validated";
        return {
            ...pill,
            disableDrag: isLocked || pill.disableDrag,
            disableStartResize: true,
            disableStopResize: true,
        };
    }

    getSelectedRecords({ startCol, endCol, startRow, endRow }) {
        const records = [];
        for (const pill of Object.values(this.pills)) {
            const row = this.rowByIds[pill.rowId];
            if (
                row.isGroup ||
                this.getFirstGridCol(pill) >= endCol ||
                this.getLastGridCol(pill) <= startCol ||
                this.getFirstGridRow(pill) >= endRow ||
                this.getLastGridRow(pill) <= startRow
            ) {
                continue;
            }
            records.push(pill.record);
        }
        return records;
    }

    getCellsInfoInContract(cellsInfo) {
        return cellsInfo.filter((c) => {
            const { employee_id } = JSON.parse(c.rowId)[0];
            const startISO = c.start.toISODate();
            const contracts = this.contractsByEmployee.get(employee_id[0]);
            if (!contracts) {
                return false;
            }
            return contracts.some(
                (c) =>
                    c["contract_date_start:day"][0] <= startISO &&
                    (startISO <= c["contract_date_end:day"][0] || !c["contract_date_end:day"][0])
            );
        });
    }

    getCellsInfoWithoutValidatedWorkEntry(cellsInfo, records) {
        return cellsInfo.filter(
            (c) =>
                !records
                    .filter((r) => r.state === "validated")
                    .map((r) => `${r.employee_id.id}|${r.date.toISODate()}`)
                    .includes(`${JSON.parse(c.rowId)[0].employee_id[0]}|${c.start.toISODate()}`)
        );
    }

    /**
     * @override
     */
    updateMultiSelection({ startCol, endCol, startRow, endRow }) {
        super.updateMultiSelection(...arguments);
        this.multiSelectionButtonsReactive.userFavoritesWorkEntries = this.userFavoritesWorkEntries;
        this.multiSelectionButtonsReactive.selection = this.getSelectedRecords(this.blockBounds);
        this.multiSelectionButtonsReactive.onQuickReplace = (multiCreateData) => {
            this.onMultiReplace(multiCreateData, this.blockBounds);
        };
        this.multiSelectionButtonsReactive.onQuickReset = () => {
            this.onResetWorkEntries(this.blockBounds);
        };
    }

    /**
     * @override
     */
    onMultiCreate(multiCreateData, { startCol, endCol, startRow, endRow }) {
        const cellsInfo = this.getCellsInfoInContract(
            this.getCellsInfo({ startCol, endCol, startRow, endRow })
        );
        return this.model.multiCreateRecords(multiCreateData, cellsInfo);
    }

    /**
     * @override
     */
    onMultiDelete({ startCol, endCol, startRow, endRow }) {
        const records = this.getSelectedRecords({ startCol, endCol, startRow, endRow });
        return this.model.unlinkRecords(
            records.filter((r) => r.state !== "validated").map((r) => r.id)
        );
    }

    onMultiReplace(multiCreateData, { startCol, endCol, startRow, endRow }) {
        const records = this.getSelectedRecords({ startCol, endCol, startRow, endRow });
        const cellsInfo = this.getCellsInfoInContract(
            this.getCellsInfoWithoutValidatedWorkEntry(
                this.getCellsInfo({ startCol, endCol, startRow, endRow }),
                records
            )
        );
        return this.model.multiReplaceRecords(
            multiCreateData,
            cellsInfo,
            records.filter((r) => r.state !== "validated")
        );
    }

    onResetWorkEntries({ startCol, endCol, startRow, endRow }) {
        const records = this.getSelectedRecords({ startCol, endCol, startRow, endRow });
        const cellsInfo = this.getCellsInfoWithoutValidatedWorkEntry(
            this.getCellsInfo({ startCol, endCol, startRow, endRow }),
            records
        );
        this.model.resetWorkEntries(
            cellsInfo,
            records.filter((r) => r.state !== "validated").map((r) => r.id)
        );
    }
}
