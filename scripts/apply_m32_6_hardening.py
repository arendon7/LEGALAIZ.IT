from __future__ import annotations

from pathlib import Path


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise SystemExit(f"No se encontró el bloque esperado en {path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> None:
    module = Path("legalai_platform/approval_desk_operations.py")
    replace_once(
        module,
        "from zipfile import ZIP_DEFLATED, ZipFile",
        "from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile",
    )
    replace_once(
        module,
        '''    def sync_portfolio(self, user: dict[str, Any], limit: int = 500) -> dict[str, Any]:
        if user.get("role") != "admin":
            raise PermissionDenied("Solo administración puede sincronizar el portafolio.")
        result = self.workspace.bootstrap(user, limit=limit)
        for case_id in result.get("created", []):
            self._append_event(case_id, "operations.initialized", user, {
                "priority": "normal",
                "sla_hours": DEFAULT_SLA_HOURS["normal"],
                "professional_approval_pending": True,
            })
        portfolio = self.portfolio(user)
        return {"schema_version": M32_6_SCHEMA, "bootstrap": result, "portfolio": portfolio["portfolio"], "metrics": portfolio["metrics"]}
''',
        '''    def sync_portfolio(self, user: dict[str, Any], limit: int = 500) -> dict[str, Any]:
        if user.get("role") != "admin":
            raise PermissionDenied("Solo administración puede sincronizar el portafolio.")
        result = self.workspace.bootstrap(user, limit=limit)
        initialized: list[str] = []
        # M32.6 también debe incorporar expedientes creados previamente en M32.5.
        # La ausencia de bitácora operativa no autoriza a sobrescribir la revisión;
        # únicamente añade el primer evento M32.6 de forma append-only.
        for row in self.workspace.list_for_user(user).get("cases", []):
            case_id = str(row.get("desk_case_id") or "")
            if not case_id:
                continue
            integrity = self.verify_chain(case_id)
            if integrity["events"]:
                continue
            self._append_event(case_id, "operations.initialized", user, {
                "priority": "normal",
                "sla_hours": DEFAULT_SLA_HOURS["normal"],
                "professional_approval_pending": row.get("status") != "released",
                "source": "portfolio_sync",
            })
            initialized.append(case_id)
        portfolio = self.portfolio(user)
        return {
            "schema_version": M32_6_SCHEMA,
            "bootstrap": result,
            "initialized": initialized,
            "initialized_count": len(initialized),
            "portfolio": portfolio["portfolio"],
            "metrics": portfolio["metrics"],
        }
''',
    )
    replace_once(
        module,
        '''        package_id = f"EXP-{current['revision_id']}-{current['sha256'][:12]}"
        filename = f"{case_id}_{package_id}_expediente_aprobacion.zip"
        target_dir = self._case_dir(case_id) / "dossiers"
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / filename
        if target.is_file():
            return target, filename
''',
        '''        approval_hash = str((detail.get("audit") or {}).get("last_hash") or "0" * 64)
        operations_hash = str(operational_integrity.get("last_hash") or "0" * 64)
        package_id = (
            f"EXP-{current['revision_id']}-{current['sha256'][:12]}-"
            f"{approval_hash[:10]}-{operations_hash[:10]}"
        )
        filename = f"{case_id}_{package_id}_expediente_aprobacion.zip"
        target_dir = self._case_dir(case_id) / "dossiers"
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / filename
        if target.is_file():
            # El nombre incorpora la revisión y los últimos hashes de ambas cadenas.
            # Una actuación nueva produce necesariamente un paquete distinto.
            try:
                with ZipFile(target) as archive:
                    required = {
                        "expediente_aprobacion.json",
                        "cadena_aprobacion.json",
                        "actividad_operativa.json",
                        "revision_vigente.json",
                        "revision_vigente.docx",
                        "LEAME.txt",
                    }
                    if not required.issubset(set(archive.namelist())):
                        raise ApprovalDeskError("El expediente almacenado está incompleto.")
                    if sha256(archive.read("revision_vigente.docx")).hexdigest() != current["sha256"]:
                        raise ApprovalDeskError("El DOCX del expediente no coincide con la revisión vigente.")
                return target, filename
            except (BadZipFile, OSError, ValueError, KeyError) as exc:
                raise ApprovalDeskError("El expediente almacenado no supera la validación de integridad.") from exc
''',
    )

    tests = Path("tests/test_m32_6_approval_operations.py")
    marker = "    def test_asignacion_es_exclusiva_de_admin_y_separa_funciones(self):\n"
    additions = '''    def test_sincronizacion_inicializa_casos_m32_5_preexistentes(self):
        created = self.workspace.bootstrap(self.admin)
        self.assertEqual(created["created_count"], 11)
        self.assertFalse((self.root / "approval-desk" / self.first_case() / "operations.jsonl").exists())
        result = self.operations.sync_portfolio(self.admin)
        self.assertEqual(result["bootstrap"]["created_count"], 0)
        self.assertEqual(result["initialized_count"], 11)
        self.assertTrue(self.operations.verify_chain(self.first_case())["valid"])
        self.assertEqual(self.operations.verify_chain(self.first_case())["events"], 1)

    def test_expediente_cambia_cuando_cambia_la_bitacora_operativa(self):
        self.sync(); self.assign_first()
        first, first_name = self.operations.export_dossier(self.admin, self.first_case())
        first_digest = sha256(first.read_bytes()).hexdigest()
        self.operations.add_note(self.legal, self.first_case(), "Nueva actuación posterior al primer expediente.")
        second, second_name = self.operations.export_dossier(self.admin, self.first_case())
        self.assertNotEqual(first_name, second_name)
        self.assertNotEqual(first_digest, sha256(second.read_bytes()).hexdigest())
        with ZipFile(second) as archive:
            dossier = json.loads(archive.read("expediente_aprobacion.json"))
        self.assertEqual(dossier["operations"]["notes"][-1]["text"], "Nueva actuación posterior al primer expediente.")

'''
    text = tests.read_text(encoding="utf-8")
    if "test_expediente_cambia_cuando_cambia_la_bitacora_operativa" not in text:
        if marker not in text:
            raise SystemExit("No se encontró el punto de inserción de pruebas M32.6")
        tests.write_text(text.replace(marker, additions + marker, 1), encoding="utf-8")

    run = Path("run.py")
    text = run.read_text(encoding="utf-8")
    compatibility = "# from legalai_platform.http_handler_m32_5 import Handler  # compatibility marker\n"
    if compatibility not in text:
        marker_run = "from legalai_platform.http_handler_m32_6 import Handler  # noqa: E402\n"
        if marker_run not in text:
            raise SystemExit("No se encontró el handler M32.6 en run.py")
        run.write_text(text.replace(marker_run, marker_run + compatibility, 1), encoding="utf-8")


if __name__ == "__main__":
    main()
