import { ListRenderer } from "@web/views/list/list_renderer"


export class AccountAuditBalanceListRenderer extends ListRenderer {
    getCellClass(column, record) {
        const classNames = super.getCellClass(column, record);
        if (column.name === 'audit_balance' && record.data.audit_balance_show_warning 
            || column.name === 'audit_previous_balance' && record.data.audit_previous_balance_show_warning) {
            return `${classNames} table-warning`;
        }
        return classNames;
    }
}
