import { WithSearch } from "@web/search/with_search/with_search";
import { patch } from "@web/core/utils/patch";

patch(WithSearch, {
    props: {
        ...WithSearch.props,
        ai: { type: Object, optional: true },
    },
});
