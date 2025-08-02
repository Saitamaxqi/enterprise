import { LivechatService } from "@im_livechat/embed/common/livechat_service";
import { patch } from "@web/core/utils/patch";

patch(LivechatService.prototype, {
    getExtraOperatorLookupParams(thread, options){
        let operatorLookupParams = super.getExtraOperatorLookupParams(thread, options);
        // 1. The agent options.ai_agent_id has higher priority than the agent specified on
        // the livechat rule matching the current URL.
        let ai_agent_id = options.ai_agent_id ?? this.store.livechat_rule?.ai_agent_id;
        operatorLookupParams['ai_agent_id'] = ai_agent_id;
        return operatorLookupParams;
    },
});
