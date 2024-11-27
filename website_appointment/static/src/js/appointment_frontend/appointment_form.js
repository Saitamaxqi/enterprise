/** @odoo-module **/

import publicWidget from "web.public.widget";
import { _t } from "web.core";
import { ReCaptcha } from "google_recaptcha.ReCaptchaV3";

publicWidget.registry.appointmentForm.include({
    init: function () {
        this._super(...arguments);
        this._recaptcha = new ReCaptcha();
        this.notification = this.bindService("notification");
    },

    willStart: async function () {
        this._recaptcha.loadLibs();
        return this._super(...arguments);
    },

    /**
     * add recaptcha before submitting
     *
     * @override
     */
    _onConfirmAppointment: async function (ev) {
        const superFunc = this._super.bind(this);
        const button = ev.target;
        const form = button.closest("form");
        if (!(await this._addRecaptchaToken(form))) {
            button.setAttribute("disabled", true);
            setTimeout(() => button.removeAttribute("disabled"), 2000);
        } else {
            superFunc(...arguments);
        }
    },

    /**
     * Add an input containing the recaptcha token if relevant
     *
     * @returns {boolean} false if form submission should be cancelled otherwise true
     */
    _addRecaptchaToken: async function (form) {
        const tokenObj = await this._recaptcha.getToken("appointment_form_submission");
        if (tokenObj.error) {
            this.notification.add(tokenObj.error, {
                sticky: true,
                title: _t("Error"),
                type: "danger",
            });
            return false;
        } else if (tokenObj.token) {
            const recaptchaTokenInput = document.createElement("input");
            recaptchaTokenInput.setAttribute("name", "recaptcha_token_response");
            recaptchaTokenInput.setAttribute("type", "hidden");
            recaptchaTokenInput.setAttribute("value", tokenObj.token);
            form.appendChild(recaptchaTokenInput);
        }
        return true;
    },
});
