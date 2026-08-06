from pathlib import Path


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"Patrón no encontrado en {path}: {old[:80]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


module = Path("legalai_platform/approval_notification_center.py")
replace_once(
    module,
    'def _clean_text(value: Any, limit: int = 1000) -> str:\n    return re.sub(r"[\\r\\n]+", " ", str(value or "")).strip()[:limit]\n',
    'def _clean_text(value: Any, limit: int = 1000) -> str:\n    return re.sub(r"[\\r\\n]+", " ", str(value or "")).strip()[:limit]\n\n\ndef _mask_email(value: Any) -> str | None:\n    text = str(value or "").strip()\n    if "@" not in text:\n        return None\n    local, domain = text.rsplit("@", 1)\n    if not local or not domain:\n        return None\n    visible = local[:1]\n    return f"{visible}{\'*\' * max(2, len(local) - 1)}@{domain}"\n',
)
replace_once(
    module,
    '                            "recipient": str(recipient.get("email")),\n',
    '                            "recipient_reference": str(recipient["id"]),\n                            "recipient_hint": _mask_email(recipient.get("email")),\n                            "recipient_address_stored": False,\n',
)
replace_once(
    module,
    '            rows.append({\n                "professional": professional,\n',
    '            rows.append({\n                "professional": {key: value for key, value in professional.items() if key != "email"},\n',
)
replace_once(
    module,
    '        now = self._now()\n        remaining = calendar.business_hours_between(now, due)\n        total = max(0.01, float(schedule["business_hours"]))\n',
    '        now = self._now()\n        start = _parse_datetime(schedule["start_at"])\n        effective_start = max(now, start)\n        remaining = calendar.business_hours_between(effective_start, due)\n        total = max(0.01, float(schedule["business_hours"]))\n',
)
replace_once(
    module,
    '        rows = [item for item in self._state()["notifications"].values() if item.get("case_id") == case_value]\n        rows.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)\n',
    '        now = self._now()\n        rows: list[dict[str, Any]] = []\n        for raw in self._state()["notifications"].values():\n            if raw.get("case_id") != case_value:\n                continue\n            if user.get("role") != "admin" and str(raw.get("recipient_id")) != str(user.get("id")):\n                continue\n            item = dict(raw)\n            item["read"] = str(user.get("id")) in raw.get("read_by", {})\n            item["acknowledged"] = bool(raw.get("acknowledged_by"))\n            item["snoozed"] = bool(raw.get("snoozed_until") and _parse_datetime(raw["snoozed_until"]) > now)\n            item["active"] = not item["acknowledged"] and not item["snoozed"]\n            item["can_manage"] = user.get("role") == "admin" or str(raw.get("recipient_id")) == str(user.get("id"))\n            rows.append(item)\n        rows.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)\n',
)

script = Path("app/modules/notification_center_m32_7.js")
replace_once(
    script,
    'function inboxItem(item,detail=false){\n  return `<article',
    'function inboxItem(item,detail=false){\n  const canManage=item.can_manage!==false;\n  return `<article',
)
replace_once(script, '${!item.read?`<button', '${canManage&&!item.read?`<button')
replace_once(script, '${!item.acknowledged?`<button class="btn secondary sm"', '${canManage&&!item.acknowledged?`<button class="btn secondary sm"')
replace_once(script, '${!item.acknowledged?`<button class="btn ghost sm"', '${canManage&&!item.acknowledged?`<button class="btn ghost sm"')

tests = Path("tests/test_m32_7_notification_center.py")
replace_once(
    tests,
    '        self.assertTrue(all(item["contains_document_content"] is False for item in outbox["messages"]))\n',
    '        self.assertTrue(all(item["contains_document_content"] is False for item in outbox["messages"]))\n        self.assertTrue(all(item["recipient_address_stored"] is False for item in outbox["messages"]))\n        self.assertTrue(all("recipient" not in item for item in outbox["messages"]))\n',
)
replace_once(
    tests,
    '        self.assertEqual(result["business_sla"]["calendar"]["name"], "Jornada interna")\n',
    '        self.assertEqual(result["business_sla"]["calendar"]["name"], "Jornada interna")\n        self.assertEqual(result["business_sla"]["business_hours_remaining"], 10)\n',
)
replace_once(
    tests,
    '        self.assertEqual(legal["overdue"], 1)\n',
    '        self.assertEqual(legal["overdue"], 1)\n        self.assertNotIn("email", legal["professional"])\n',
)

workflow = Path(".github/workflows/m32-7-notification-center.yml")
replace_once(
    workflow,
    "          assert payload['outbox_contains_document_content'] is False\n",
    "          assert payload['outbox_contains_document_content'] is False\n          assert payload['outbox_recipient_addresses_stored'] is False\n",
)

runner = Path("scripts/run_m32_7_notification_center.py")
replace_once(
    runner,
    '            "outbox_contains_document_content": any(item["contains_document_content"] for item in outbox["messages"]),\n',
    '            "outbox_contains_document_content": any(item["contains_document_content"] for item in outbox["messages"]),\n            "outbox_recipient_addresses_stored": any(item.get("recipient_address_stored", True) for item in outbox["messages"]),\n',
)
