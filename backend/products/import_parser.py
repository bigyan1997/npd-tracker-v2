import csv
import io

from . import fields_schema as schema

YES_VALUES = {"y", "yes", "true", "1"}
NO_VALUES = {"n", "no", "false", "0"}

_LABEL_TO_KEY = {f["label"].strip().lower(): f["key"] for f in schema.FIELDS}
_KEY_TO_KEY = {f["key"].strip().lower(): f["key"] for f in schema.FIELDS}
_IGNORED_HEADERS = {"recordid", "lasteditedby", "lasteditedat"}
_STATUS_OPTIONS_BY_LOWER = {
    o.lower(): o for o in schema.FIELDS_BY_KEY["status"]["options"]
}


class ParseError(Exception):
    pass


def _match_header(header):
    normalized = header.strip().lower()
    if normalized in _IGNORED_HEADERS:
        return None
    return _LABEL_TO_KEY.get(normalized) or _KEY_TO_KEY.get(normalized)


def _normalize_yn(value):
    v = value.strip().lower()
    if v in YES_VALUES:
        return "Y", None
    if v in NO_VALUES:
        return "N", None
    return value, f"'{value}' is not a recognized Yes/No value"


def _normalize_status(value):
    v = value.strip()
    match = _STATUS_OPTIONS_BY_LOWER.get(v.lower())
    if match:
        return match, None
    return value, f"'{value}' does not match a known status option"


def parse_csv(file):
    try:
        text = file.read().decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ParseError("Could not read file — please upload a UTF-8 encoded CSV.") from exc

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ParseError("The file has no header row.")

    header_map = {}
    unmapped_columns = []
    for header in reader.fieldnames:
        key = _match_header(header)
        if key:
            header_map[header] = key
        elif header.strip().lower() not in _IGNORED_HEADERS:
            unmapped_columns.append(header)

    rows = []
    for row_number, raw_row in enumerate(reader, start=2):
        data = {}
        errors = []
        warnings = []

        for header, key in header_map.items():
            value = (raw_row.get(header) or "").strip()
            field = schema.FIELDS_BY_KEY[key]
            if field["type"] == "yn" and value:
                value, warning = _normalize_yn(value)
                if warning:
                    warnings.append(f"{field['label']}: {warning}")
            elif key == "status" and value:
                value, warning = _normalize_status(value)
                if warning:
                    warnings.append(f"{field['label']}: {warning}")
            elif field["type"] == "number" and value:
                try:
                    float(value)
                except ValueError:
                    warnings.append(f"{field['label']}: '{value}' is not a number")
            data[key] = value

        if not data.get("product", "").strip():
            errors.append("Product name is required.")

        rows.append({
            "rowNumber": row_number,
            "data": data,
            "errors": errors,
            "warnings": warnings,
        })

    return rows, unmapped_columns
