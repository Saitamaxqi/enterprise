import { Chatter } from "@mail/chatter/web_portal/chatter";
export class BankRecChatter extends Chatter {
    static props = [...Chatter.props, "statementLine"];

    /**
     * This method extends the Chatter `load` method and ensures that the statement line is reloaded
     * after the thread and request list are loaded. Used for the activity icon.
     *
     * @param {Object} thread - The thread to load.
     * @param {Array} requestList - A list of requests to load.
     */
    load(thread, requestList) {
        super.load(thread, requestList);
        this.props.statementLine?.load();
    }

    /**
     * This method extends the Chatter `onUploaded` method, ensuring that after the upload,
     * the statement line data is reloaded to reflect any changes. Used for the attachment icon.
     *
     * @param {Object} data - The uploaded data.
     */
    async onUploaded(data) {
        await super.onUploaded(data);
        this.props.statementLine?.load();
    }
}
