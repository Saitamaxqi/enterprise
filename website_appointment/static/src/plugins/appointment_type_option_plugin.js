import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { _t } from '@web/core/l10n/translation';
import { Cache } from "@web/core/utils/cache";

class AppointmentTypeOptionPlugin extends Plugin {
    static id = "AppointmentTypeOption";
    resources = {
        builder_options: {
            template: "website_appointment.AppointmentTypeOption",
            selector: "main:has(.o_wappointment_type_options)",
            editableOnly: false,
            title: _t("Appointment Type"),
            groups: ["website.group_website_designer"],
        },
        builder_actions: this.getActions(),
    };
    setup() {
        this.appointmentTypeId = Number(this.document.documentElement.querySelector(".o_wappointment_type_options")?.dataset.appointmentTypeId);
        this.appointmentTypeCache = new Cache(this._fetchAppointmentType.bind(this), JSON.stringify);
    }
    async _fetchAppointmentType() {
        return (await this.services.orm.read(
            "appointment.type",
            [this.appointmentTypeId],
            ["allow_guests", "avatars_display", "hide_duration", "hide_timezone"]
        ))[0];
    }
    getActions() {
        return {
            appointmentTypeShowTimezone: this.buildAction("hide_timezone", false, true),
            appointmentTypeShowDuration: this.buildAction("hide_duration", false, true),
            appointmentTypeShowAvatars: this.buildAction("avatars_display", "show", "hide"),
            appointmentTypeShowAllowGuests: this.buildAction("allow_guests", false, true),
        };
    }
    buildAction(fieldName, applyValue, clearValue) {
        const set = async (apply) => {
            await this.services.orm.write("appointment.type", [this.appointmentTypeId], {
                [fieldName]: apply ? applyValue : clearValue,
            });
        };
        return {
            isReload: true,
            prepare: async () => {
                this.appointmentType = await this.appointmentTypeCache.read();
            },
            isApplied: () => {
                return this.appointmentType[fieldName] === applyValue;
            },
            load: async () => {
                const wasApplied = this.appointmentType[fieldName] === applyValue;
                await set(!wasApplied);
            },
            apply: () => {},
            clear: () => {},
        };
    }
}

registry
    .category("website-plugins")
    .add(AppointmentTypeOptionPlugin.id, AppointmentTypeOptionPlugin);
