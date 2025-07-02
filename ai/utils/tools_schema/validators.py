from odoo.exceptions import ValidationError

from .param_schema_validator import ParamSchemaValidator
from .param_llm_value_validator import ParamLLMValueValidator


def validate_input(function_description, input_schema, required_parameters):
    if not isinstance(function_description, str) or not function_description.strip():
        raise ValueError("function_description should be a non-empty string")
    if (
        required_parameters is None
        or not isinstance(required_parameters, list)
    ):
        raise ValueError(
            "The required properties should be specified as a list. i.e. 'required': [<property1_name>, <property2_name>, ...]."
            "If no properties are required, set required to an empty list 'required': []"
        )
    if any(
        required_property not in input_schema
        for required_property in required_parameters
    ):
        raise ValueError(
            "Some properties are required but their definition is missing in the schema"
        )


def validate_schema(schema):
    description = schema.get("description")
    parameters = schema.get("parameters").get("properties")
    required_parameters = schema.get("parameters").get("required")
    validate_input(description, parameters, required_parameters)
    for param_name, param_definition in parameters.items():
        param_validator = ParamSchemaValidator(param_name, param_definition)
        param_validator._validate()


def validate_params_llm_values_with_schema(instance, schema, required_parameters):
    errors = []
    for param_name, param_definition in schema.items():
        param_validator = ParamLLMValueValidator(
            param_name=param_name,
            expected_param=param_definition,
            param_llm_value=instance.get(param_name),
            is_param_required=param_name in required_parameters,
        )
        try:
            param_validator._validate()
        except (ValueError, TypeError) as e:
            errors.append(str(e))
    if errors:
        raise ValidationError("\n\n".join(errors))
