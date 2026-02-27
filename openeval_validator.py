import json
import os
from typing import Any

_SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "item_schema.json")
_schema_cache: dict | None = None


def _load_schema() -> dict:
    global _schema_cache
    if _schema_cache is None:
        with open(_SCHEMA_PATH) as f:
            _schema_cache = json.load(f)
    return _schema_cache


def _tag_parts(schema_str: str) -> list[str]:
    """Extract modifier tokens from a '[type, modifier] ...' schema string."""
    close = schema_str.find('] ')
    if close == -1:
        close = schema_str.rfind(']')
    return [p.strip() for p in schema_str[1:close].split(',')]


def _classify(schema_value: Any) -> str:
    """
    Classify a schema value into one of:
      'auto'              - tag contains 'auto'; field is system-generated, skip
      'optional'          - tag contains 'optional'; field may be absent, skip
      'required_str'      - plain string tag; field must be present but can be empty
      'required_any'      - '[any]' tag; field must be present, any value type accepted
      'required_numeric'  - '[int]', '[float]', '[bool]', or '[int or float]' tag; field
                            must be present and its value must be a number
      'required_dict'     - dict; field must be present as a dict, recurse
      'required_list_str' - '[list[...]]' tag or list with plain-string template;
                            field must be present as a list; if the key ends with
                            '_content' or is 'responses', the list must also be non-empty
      'required_list_dict'- list with dict template; field must be present as a list,
                            each element validated; if the key ends with '_content'
                            or is 'responses', the list must also be non-empty
    """
    if isinstance(schema_value, str):
        parts = _tag_parts(schema_value)
        if 'auto' in parts:
            return 'auto'
        if 'optional' in parts:
            return 'optional'
        if parts[0].startswith('list['):
            return 'required_list_str'
        if parts[0] == 'any':
            return 'required_any'
        type_tokens = {t.strip() for t in parts[0].split(' or ')}
        if type_tokens and type_tokens <= {'int', 'float', 'bool'}:
            return 'required_numeric'
        return 'required_str'

    if isinstance(schema_value, dict):
        return 'required_dict'

    if isinstance(schema_value, list) and schema_value:
        item = schema_value[0]
        if isinstance(item, str):
            parts = _tag_parts(item)
            if 'auto' in parts or 'optional' in parts:
                return 'optional'
            return 'required_list_str'
        if isinstance(item, dict):
            return 'required_list_dict'

    return 'auto'  # empty list or unrecognised type → skip


def _validate(
    data: Any,
    schema: dict,
    violations: list[dict],
    path: str = "",
) -> None:
    """Recursively walk *schema* and record violations found in *data*."""
    if not isinstance(data, dict):
        violations.append({"field": path, "field_desc": "OPENEVAL ITEM IN JSON FORMAT", "violation_type": TypeError})
        return

    for key, schema_value in schema.items():
        field_path = f"{path}.{key}" if path else key
        kind = _classify(schema_value)

        if kind in ("auto", "optional"):
            continue

        elif kind == "required_str":
            if key not in data:
                violations.append({"field": field_path, "field_desc": schema_value, "violation_type": KeyError})
            elif data[key] is None:
                violations.append({"field": field_path, "field_desc": schema_value, "violation_type": ValueError})
            elif not isinstance(data[key], str):
                violations.append({"field": field_path, "field_desc": schema_value, "violation_type": TypeError})

        elif kind == "required_any":
            if key not in data:
                violations.append({"field": field_path, "field_desc": schema_value, "violation_type": KeyError})

        elif kind == "required_numeric":
            if key not in data:
                violations.append({"field": field_path, "field_desc": schema_value, "violation_type": KeyError})
            else:
                v = data[key]
                type_tokens = {t.strip() for t in _tag_parts(schema_value)[0].split(' or ')}
                valid = False
                if 'bool' in type_tokens:
                    valid = valid or isinstance(v, bool)
                if 'int' in type_tokens:
                    valid = valid or (isinstance(v, int) and not isinstance(v, bool))
                if 'float' in type_tokens:
                    valid = valid or (isinstance(v, (int, float)) and not isinstance(v, bool))
                if not valid:
                    violations.append({"field": field_path, "field_desc": schema_value, "violation_type": TypeError})

        elif kind == "required_dict":
            if key not in data:
                violations.append({"field": field_path, "field_desc": schema_value, "violation_type": KeyError})
            elif not isinstance(data[key], dict):
                violations.append({"field": field_path, "field_desc": schema_value, "violation_type": TypeError})
            else:
                _validate(data[key], schema_value, violations, field_path)

        elif kind == "required_list_str":
            if key not in data:
                violations.append({"field": field_path, "field_desc": schema_value, "violation_type": KeyError})
            elif not isinstance(data[key], list):
                violations.append({"field": field_path, "field_desc": schema_value, "violation_type": TypeError})
            else:
                if (key.endswith('_content') or key == 'responses') and len(data[key]) == 0:
                    violations.append({"field": field_path, "field_desc": schema_value, "violation_type": ValueError})
                if isinstance(schema_value, str):
                    inner_type_str = _tag_parts(schema_value)[0][5:-1]  # "list[str]" -> "str"
                elif isinstance(schema_value, list) and schema_value:
                    inner_type_str = _tag_parts(schema_value[0])[0]  # e.g., "str or dict"
                else:
                    inner_type_str = None
                if inner_type_str:
                    _type_map = {'str': str, 'dict': dict, 'int': int, 'float': float, 'bool': bool}
                    allowed = tuple(_type_map[t.strip()] for t in inner_type_str.split(' or ') if t.strip() in _type_map)
                    if allowed:
                        for i, elem in enumerate(data[key]):
                            if not isinstance(elem, allowed):
                                violations.append({"field": f"{field_path}[{i}]", "field_desc": schema_value, "violation_type": TypeError})

        elif kind == "required_list_dict":
            if key not in data:
                violations.append({"field": field_path, "field_desc": schema_value, "violation_type": KeyError})
            elif not isinstance(data[key], list):
                violations.append({"field": field_path, "field_desc": schema_value, "violation_type": TypeError})
            else:
                if (key.endswith('_content') or key == 'responses') and len(data[key]) == 0:
                    violations.append({"field": field_path, "field_desc": schema_value, "violation_type": ValueError})
                template = schema_value[0]
                for i, item in enumerate(data[key]):
                    _validate(item, template, violations, f"{field_path}[{i}]")


def validate_entry(entry: dict) -> tuple[bool, list[dict]]:
    """
    Validate a JSON entry against the OpenEval item schema:
    1) Fields whose schema description starts with [AUTO] are system-generated and not required from the contributor.
    2) Fields starting with [OPTIONAL] may be absent.
    3) All other fields are required with type restrictions. If they don't apply, please use empty values.
    4) Fields whose name ends with '_content' or is 'responses' must be non-empty lists.

    Args:
        entry: The item entry dict to validate.

    Returns:
        (is_valid, violations)
        - is_valid:   True when no violations were found.
        - violations: List of violation dicts, each with keys:
            *field*          – dot-path to the problematic key
                                (e.g. 'item_metadata.contributor.email')
            *field_desc*     – corresponding value of the 
                                problematic key in the schema
            *violation_type* – exception class describing the problem
                                (KeyError: missing fields, ValueError: null values or
                                empty '_content'/'responses' lists, TypeError: wrong types)
    """
    schema = _load_schema()
    violations: list[dict] = []
    _validate(entry, schema, violations)
    return len(violations) == 0, violations


if __name__ == '__main__':
    with open('item_test.json', 'r') as f:
        examples = json.load(f)
    for i, e in enumerate(examples):
        print(f'Item #{i}:')
        res, vios = validate_entry(e)
        print(res)
        if not res:
            for j, v in enumerate(vios):
                print(f'{j + 1}. {v}')