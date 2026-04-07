from collections.abc import Mapping


def _clean_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def build_contract_metadata_from_template(
    template_key: str | None,
    template_config: Mapping[str, object] | None,
) -> dict[str, object]:
    if not template_key or not template_config:
        return {}

    category = _clean_text(template_config.get("category"))
    subcategory = _clean_text(template_config.get("subcategory"))
    subject = _clean_text(template_config.get("subject"))
    reference_asset = _clean_text(template_config.get("reference_asset"))
    threshold_value = _clean_text(template_config.get("threshold_value"))
    timeframe_label = _clean_text(template_config.get("timeframe_label"))
    interval_label = _clean_text(template_config.get("interval_label"))
    reference_source_label = _clean_text(template_config.get("reference_source_label"))
    reference_price = _clean_text(template_config.get("reference_price"))
    reference_timestamp = _clean_text(template_config.get("reference_timestamp"))
    reference_label = _clean_text(template_config.get("reference_label"))
    contract_notes = _clean_text(template_config.get("contract_notes"))

    derived_reference_label = reference_label or reference_source_label or reference_asset or subject
    derived_category = category or "Markets"
    derived_subcategory = subcategory or subject

    if template_key == "price_above":
        notes = contract_notes or (
            f"This market resolves Yes if {subject or reference_asset or 'the asset'} closes above {threshold_value or 'the target'}"
            f"{f' {timeframe_label}' if timeframe_label else ''}."
        )
        return {
            "contract_type": "price_above",
            "category": derived_category,
            "subcategory": derived_subcategory,
            "reference_label": derived_reference_label,
            "reference_source_label": reference_source_label,
            "reference_asset": reference_asset,
            "reference_price": reference_price,
            "price_to_beat": threshold_value,
            "reference_timestamp": reference_timestamp,
            "notes": notes,
        }

    if template_key == "price_below":
        notes = contract_notes or (
            f"This market resolves Yes if {subject or reference_asset or 'the asset'} closes below {threshold_value or 'the target'}"
            f"{f' {timeframe_label}' if timeframe_label else ''}."
        )
        return {
            "contract_type": "price_below",
            "category": derived_category,
            "subcategory": derived_subcategory,
            "reference_label": derived_reference_label,
            "reference_source_label": reference_source_label,
            "reference_asset": reference_asset,
            "reference_price": reference_price,
            "price_to_beat": threshold_value,
            "reference_timestamp": reference_timestamp,
            "notes": notes,
        }

    if template_key == "up_down_interval":
        notes = contract_notes or (
            f"This market resolves Yes if {subject or reference_asset or 'the asset'} is up over the stated interval"
            f"{f' of {interval_label}' if interval_label else ''}."
        )
        return {
            "contract_type": "up_down_interval",
            "category": derived_category,
            "subcategory": derived_subcategory,
            "reference_label": derived_reference_label,
            "reference_source_label": reference_source_label,
            "reference_asset": reference_asset,
            "reference_price": reference_price,
            "price_to_beat": reference_price,
            "reference_timestamp": reference_timestamp,
            "notes": notes,
        }

    if template_key == "event_outcome":
        notes = contract_notes or (
            f"This market resolves according to the official outcome of {subject or 'the named event'}"
            f"{f' {timeframe_label}' if timeframe_label else ''}."
        )
        return {
            "contract_type": "event_outcome",
            "category": derived_category,
            "subcategory": derived_subcategory,
            "reference_label": derived_reference_label,
            "reference_source_label": reference_source_label,
            "reference_asset": reference_asset,
            "reference_price": reference_price,
            "reference_timestamp": reference_timestamp,
            "notes": notes,
        }

    return {}
