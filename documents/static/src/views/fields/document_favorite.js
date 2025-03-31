import { registry } from "@web/core/registry";
import {
  BooleanFavoriteField,
  booleanFavoriteField,
} from "@web/views/fields/boolean_favorite/boolean_favorite_field";

export class DocumentFavoriteField extends BooleanFavoriteField {
  /** Override **/
  async update() {
    if (this.props.readonly) {
      return;
    }
    const result = await this.props.record.model.orm.call(
        "documents.document",
        "toggle_favorited",
        [this.props.record.resId]
    );
    this.props.record.data[this.props.name] = result;
  }
}

export const documentFavoriteField = {
  ...booleanFavoriteField,
  component: DocumentFavoriteField,
};

registry.category("fields").add("document_favorite", documentFavoriteField);
