import re


class ParamLLMValueValidator:
    # TODO: refactor to not use a class and find a better name (does not only validate)
    JSON_SCHEMA_TO_PYTHON_TYPE = {
        'string': str,
        'integer': int,
        'number': (float, int),
        'boolean': bool,
        'array': list,
        'object': dict,
    }

    def __init__(self, param_name, expected_param, param_llm_value, is_param_required):
        self.param_name = param_name
        self.expected_param = expected_param
        self.param_llm_value = param_llm_value
        self.is_param_required = is_param_required
        self.expected_param_type = expected_param['type']

    def _validate(self):
        if self.is_param_required and self.param_llm_value is None:
            raise ValueError(f"Could you please provide info about '{self.param_name}' as it is required to process your request")
        # An optional parameter (parameter that is not required) can be send by the llm. It will have the value None
        if not self.param_llm_value:
            return

        if not isinstance(self.param_llm_value, self.JSON_SCHEMA_TO_PYTHON_TYPE[self.expected_param_type]):
            raise TypeError(f"The type of the parameter '{self.param_name}' is incorrect. It should be '{self.expected_param_type}'.")

        expected_pattern = self.expected_param_type == 'string' and self.expected_param.get('pattern', False)
        if expected_pattern and not re.fullmatch(expected_pattern, self.param_llm_value):
            raise ValueError(f"The value '{self.param_llm_value}' of the parameter '{self.param_name}' doesn't match the expected pattern '{expected_pattern}'.")

        if self.expected_param_type == 'array':
            self._perform_array_type_checks()
        if self.expected_param_type == 'object':
            self._perform_object_type_checks()

        max_length = self.expected_param.get("maxLength")
        if isinstance(self.param_llm_value, str) and max_length and len(self.param_llm_value) > max_length:
            # On the 31 Jully 2025, Gemini does not respect the `maxLength` JSON schema
            # (while OpenAI does), so we manually truncate the arguments if needed
            self.param_llm_value = self.param_llm_value[:max_length] + "..."

        return self.param_llm_value

    def _perform_array_type_checks(self):
        self._validate_array_item_types()
        self._validate_array_item_pattern()

    def _validate_array_item_types(self):
        array_item_types = self.expected_param['items']
        array_item_types = array_item_types.get('anyOf', [array_item_types])
        array_item_types = [item['type'] for item in array_item_types]
        for item in self.param_llm_value:
            if not any(isinstance(item, self.JSON_SCHEMA_TO_PYTHON_TYPE[array_item_type]) for array_item_type in array_item_types):
                raise ValueError(f"Some of the items of the array parameter '{self.param_name}' have an incorrect type. The valid types are '{array_item_types}'")

    def _validate_array_item_pattern(self):
        expected_pattern = self.expected_param.get('pattern', False)

        if not expected_pattern:
            return

        for item in self.param_llm_value:
            if not re.fullmatch(expected_pattern, item):
                raise ValueError(f"The value '{item}' of one of the items of the array parameter '{self.param_name}' doesn't match the expected pattern '{expected_pattern}'.")

    def _perform_object_type_checks(self):
        object_properties = self.expected_param['properties']
        required_properties = self.expected_param['required']
        for property_name, property_definition in object_properties.items():
            param_validator = ParamLLMValueValidator(
                param_name=property_name,
                expected_param=property_definition,
                param_llm_value=self.param_llm_value.get(property_name),
                is_param_required=property_name in required_properties
            )
            self.param_llm_value[property_name] = param_validator._validate()
