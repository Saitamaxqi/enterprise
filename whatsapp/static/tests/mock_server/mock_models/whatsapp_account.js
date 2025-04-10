import { getKwArgs, models } from "@web/../tests/web_test_helpers";

export class WhatsAppAccount extends models.ServerModel {
    _name = "whatsapp.account";

    _records = [{ id: 1, name: "Test Account" }];

    /** @param {number[]} ids */
    _to_store(ids, store, fields) {
        const kwargs = getKwArgs(arguments, "ids", "store", "fields");
        fields = kwargs.fields;
        store.add(this._name, this._read_format(ids, fields, false));
    }
}
