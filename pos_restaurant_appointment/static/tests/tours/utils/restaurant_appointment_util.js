import { negate } from "@point_of_sale/../tests/generic_helpers/utils";

export function appointmentLabel(table_num, appointment_name) {
    return [
        {
            content: `Appointment label ${appointment_name}, is present underneath table ${table_num}`,
            trigger: `.floor-map .table:has(.label:contains("${table_num}"):has(.appointment-label:contains("${appointment_name}"))`,
        },
    ];
}

export function checkAppointmentLabelNotPresent(table_num, appointment_name) {
    return [
        {
            content: `Appointment "${appointment_name}" should NOT appear under table ${table_num}`,
            trigger: negate(
                `.appointment-label:contains("${appointment_name}")`,
                `.table:has(.label:contains("${table_num}"))`
            ),
        },
    ];
}
