import { Plugin } from "@html_editor/plugin";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { OnlineAppointmentOption } from "./online_appointment_option";

class OnlineAppointmentOptionPlugin extends Plugin {
    static id = "OnlineAppointmentOption";

    async setup() {
        this.fetchAppointmentTypesProm = null;
        this.allAppointmentTypesById = null;
    }

    resources = {
        builder_actions: this.getActions(),
        builder_options: {
            OptionComponent: OnlineAppointmentOption,
            selector: ".s_online_appointment",
            props: this.getComponentProps(),
        },
        so_content_addition_selector: [".s_online_appointment"],
    };

    getActions() {
        return {
            setAppTypes: {
                apply: ({ editingElement, value }) => {
                    this.setDatasetProperty(
                        editingElement,
                        "appointmentTypes",
                        JSON.parse(value).map((appType) => appType.id)
                    );
                },
                getValue: ({ editingElement }) => {
                    const selectedAppointmentTypes = this.getDatasetProperty(
                        editingElement,
                        "appointmentTypes",
                        true
                    );
                    const appointmentTypesDetails = selectedAppointmentTypes.map((id) => {
                        const appointmentType = this.allAppointmentTypesById[id];
                        return { id: appointmentType.id, name: appointmentType.name };
                    });
                    return JSON.stringify(appointmentTypesDetails);
                },
            },
            setStaffUsers: {
                apply: ({ editingElement, value }) => {
                    this.setDatasetProperty(
                        editingElement,
                        "staffUsers",
                        JSON.parse(value).map((user) => user.id)
                    );
                },
                getValue: ({ editingElement }) => {
                    const selectedAppointmentTypes = this.getDatasetProperty(
                        editingElement,
                        "appointmentTypes",
                        true
                    );
                    if (
                        selectedAppointmentTypes.length !== 1 ||
                        this.getDatasetProperty(editingElement, "targetUsers") === "all"
                    ) {
                        return "[]";
                    }
                    const appointmentTypeData =
                        this.allAppointmentTypesById[selectedAppointmentTypes[0]];
                    const selectedUserIds = this.getDatasetProperty(
                        editingElement,
                        "staffUsers",
                        true
                    );
                    const staffUsersDetails = appointmentTypeData.staff_users
                        .filter((user) => selectedUserIds.includes(user.id))
                        .map(({ id, name }) => ({ id, name, display_name: name }));
                    return JSON.stringify(staffUsersDetails);
                },
            },
        };
    }

    getComponentProps() {
        return {
            setDatasetProperty: this.setDatasetProperty.bind(this),
            getDatasetProperty: this.getDatasetProperty.bind(this),
            fetchAppointmentTypes: this._fetchAppointmentTypes.bind(this),
        };
    }

    async _fetchAppointmentTypes() {
        if (!this.fetchAppointmentTypesProm) {
            this.fetchAppointmentTypesProm = rpc("/appointment/get_snippet_data");
            this.allAppointmentTypesById = await this.fetchAppointmentTypesProm;
        }
        return this.fetchAppointmentTypesProm;
    }

    /**
     * Set a target dataset attribute value and trigger cascading updates as
     * necessary. Finally, update the link's form unless prevented.
     *
     * @param {"targetTypes" | "appointmentTypes" | "targetUsers" | "staffUsers" } property
     * @param {String | number[]} value
     */
    setDatasetProperty(el, property, value) {
        if (property === "targetTypes") {
            // Change if all or a selection of appointment types. Reset all subsequent parameters
            if (this.getDatasetProperty(el, "targetTypes") !== value) {
                el.dataset.targetTypes = value;
                if (this.getDatasetProperty(el, "appointmentTypes", true).length) {
                    this.setDatasetProperty(el, "appointmentTypes", []);
                }
            }
            this.setDatasetProperty(el, "targetUsers", "all");
        } else if (property === "appointmentTypes") {
            el.dataset.appointmentTypes = JSON.stringify(value);
            this.setDatasetProperty(el, "targetUsers", "all");
        } else if (property === "targetUsers") {
            el.dataset.targetUsers = value;
            if (
                value !== "specify" ||
                this.getDatasetProperty(el, "appointmentTypes", true).length !== 1
            ) {
                this.setDatasetProperty(el, "staffUsers", []);
            }
        } else if (property === "staffUsers") {
            el.dataset.staffUsers = JSON.stringify(value);
        }
    }

    /**
     * Helper method to retrieve target dataset properties to increase other
     * methods' readability.
     *
     * @param {String} property Name of the target dataset property
     * @param {boolean} parsed `true` to apply JSON.parse before returning
     * @returns {(String | Number[])}
     */
    getDatasetProperty(el, property, parsed = false) {
        const value = el.dataset[property];
        return parsed ? JSON.parse(value) : value;
    }
}

registry
    .category("website-plugins")
    .add(OnlineAppointmentOptionPlugin.id, OnlineAppointmentOptionPlugin);
