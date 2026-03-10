import json
import jsonlines
import os
from typing import Any
import re

_SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "item_schema.json")
_schema_cache: dict | None = None

_TYPE_MAP = {'str': str, 'dict': dict, 'int': int, 'float': float, 'bool': bool}

# dict-valued schema fields that are optional (may be absent entirely)
_OPTIONAL_DICT_KEYS = {'contributor'}

# dict-template list fields that must be non-empty
_NON_EMPTY_LIST_KEYS = {'responses', 'scores'}


def _load_schema() -> dict:
    global _schema_cache
    if _schema_cache is None:
        with open(_SCHEMA_PATH) as f:
            _schema_cache = json.load(f)
    return _schema_cache


def _parse_constraints(schema_str: str) -> list[str]:
    """
    Extract dtype and presence constraints from a '[dtype | presense] ...' schema string.
    The dtype constraints specify the allowed data type(s) of the schema value.
    The presence constraints are as follows:
        'auto'          - field is system-generated, skip
        'optional'      - field may be absent, skip
        'required'      - field must be present but can be empty
        'non-empty'     - field must be present and non-empty
    Returns [dtype_str, presence_str], e.g. ['str,dict', 'non-empty'].
    """
    match = re.match(r'\[(.+)\]', schema_str)
    if not match:
        return ['str', 'required']
    parts = [p.strip() for p in match.group(1).split('|')]
    dtype = parts[0]
    presence = parts[1] if len(parts) > 1 else 'required'
    return [dtype, presence]


def _type_ok(val: Any, dtype: str) -> bool:
    """
    Return True if val matches any type in the dtype string.
    dtype examples: 'any', 'str', 'str,dict', 'list[str,dict]', 'int,float,bool', 'float'
    'any'         - always passes, no type restriction.
    'list[...]'   - only checks that val is a list (element types checked in _validate).
    'float'       - accepts int values (JSON numbers are untyped).
    bool is excluded from int matches to avoid Python's bool-is-int overlap.
    """
    if dtype == 'any':
        return True
    if dtype.startswith('list['):
        return isinstance(val, list)
    for t in (s.strip() for s in dtype.split(',')):
        if t == 'bool' and isinstance(val, bool):
            return True
        if t == 'int' and isinstance(val, int) and not isinstance(val, bool):
            return True
        if t == 'float' and isinstance(val, (int, float)) and not isinstance(val, bool):
            return True
        if t in _TYPE_MAP and isinstance(val, _TYPE_MAP[t]):
            return True
    return False


def _validate(
    data: Any,
    schema: dict,
    violations: list[dict],
    path: str = "",
) -> None:
    """Recursively walk *schema* and record violations found in *data*."""
    if not isinstance(data, dict):
        violations.append({"field": '/', "field_desc": "OPENEVAL ITEM IN JSON FORMAT", "violation_type": TypeError})
        return

    for sch_key, sch_value in schema.items():
        field_path = f"{path}.{sch_key}" if path else sch_key

        # --- leaf field: sch_value is a description ---
        if isinstance(sch_value, str):
            dtype, presence = _parse_constraints(sch_value)

            if presence == 'auto':
                continue

            if presence == 'optional':
                if sch_key not in data:
                    continue
                # present but wrong type
                val = data[sch_key]
                if val is not None and not _type_ok(val, dtype):
                    violations.append({"field": field_path, "field_desc": sch_value, "violation_type": TypeError})
                continue

            # presence is 'required' or 'non-empty'
            if sch_key not in data:
                violations.append({"field": field_path, "field_desc": sch_value, "violation_type": KeyError})
                continue

            val = data[sch_key]

            if presence == 'non-empty':
                if val is None:
                    violations.append({"field": field_path, "field_desc": sch_value, "violation_type": ValueError})
                    continue
                elif isinstance(val, (str, list)) and len(val) == 0:
                    violations.append({"field": field_path, "field_desc": sch_value, "violation_type": ValueError})
                    continue

            if presence == 'required' and val is None:
                continue

            if not _type_ok(val, dtype):
                violations.append({"field": field_path, "field_desc": sch_value, "violation_type": TypeError})
                continue

            if presence == 'non-empty' and isinstance(val, (str, list)) and len(val) == 0:
                violations.append({"field": field_path, "field_desc": sch_value, "violation_type": ValueError})
                continue

            # for list[inner] dtypes, also validate inner element types
            if dtype.startswith('list['):
                inner_dtype = dtype[5:-1]  # 'list[str,dict]' -> 'str,dict'
                for i, elem in enumerate(val):
                    if not _type_ok(elem, inner_dtype):
                        violations.append({"field": f"{field_path}[{i}]", "field_desc": sch_value, "violation_type": TypeError})

        # --- nested mapping ---
        elif isinstance(sch_value, dict):
            if sch_key not in data:
                if sch_key in _OPTIONAL_DICT_KEYS:
                    continue
                violations.append({"field": field_path, "field_desc": sch_value, "violation_type": KeyError})
                continue
            if not isinstance(data[sch_key], dict):
                violations.append({"field": field_path, "field_desc": sch_value, "violation_type": TypeError})
                continue
            _validate(data[sch_key], sch_value, violations, field_path)

        # --- list field ---
        elif isinstance(sch_value, list) and sch_value:
            if sch_key not in data:
                violations.append({"field": field_path, "field_desc": sch_value, "violation_type": KeyError})
                continue
            if not isinstance(data[sch_key], list):
                violations.append({"field": field_path, "field_desc": sch_value, "violation_type": TypeError})
                continue

            lst = data[sch_key]
            template = sch_value[0]

            if isinstance(template, str):   # currently idle
                # list of scalars — template string encodes element constraints
                dtype, presence = _parse_constraints(template)
                if presence == 'non-empty' and len(lst) == 0:
                    violations.append({"field": field_path, "field_desc": sch_value, "violation_type": ValueError})
                for i, elem in enumerate(lst):
                    elem_path = f"{field_path}[{i}]"
                    if elem is None:
                        violations.append({"field": elem_path, "field_desc": template, "violation_type": ValueError})
                        continue
                    if not _type_ok(elem, dtype):
                        violations.append({"field": elem_path, "field_desc": template, "violation_type": TypeError})

            elif isinstance(template, dict):
                # list of objects — non-empty check for designated keys
                if sch_key in _NON_EMPTY_LIST_KEYS and len(lst) == 0:
                    violations.append({"field": field_path, "field_desc": template, "violation_type": ValueError})
                for i, elem in enumerate(lst):
                    _validate(elem, template, violations, f"{field_path}[{i}]")


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
    # load your item examples
    file_path = 'item_examples.json'
    if file_path.endswith('.jsonl'):   # jsonl
        with jsonlines.open(file_path, 'r') as f:
            examples = [o for o in f]
    else:   # json
        assert file_path.endswith('.json')
        with open(file_path, 'r') as f:
            examples = json.load(f)

    # validate the examples and print violations
    for i, e in enumerate(examples):
        res, vios = validate_entry(e)
        if not res:
            print(f'Item #{i}')
            for j, v in enumerate(vios):
                print(f'{j + 1}. {v}')
            print()
    print('Done!')