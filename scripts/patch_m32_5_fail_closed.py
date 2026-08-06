from pathlib import Path


def replace_exact(path: str, old: str, new: str) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"No se encontró el bloque exacto en {path}")
    target.write_text(text.replace(old, new), encoding="utf-8")


replace_exact(
    "legalai_platform/approval_desk_workspace.py",
    '''    def _workflow_state(detail: dict[str, Any]) -> str:
        case = detail.get("case", {})
        if case.get("status") == "released":
            return "released"
''',
    '''    def _workflow_state(detail: dict[str, Any]) -> str:
        case = detail.get("case", {})
        if not bool(detail.get("audit", {}).get("valid")):
            return "audit_invalid"
        if case.get("status") == "released":
            return "released"
''',
)

replace_exact(
    "legalai_platform/approval_desk_workspace.py",
    '''        detected, digest, security_status = self.upload_validator(filename, data)
        if detected != "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            raise ApprovalDeskError("La revisión debe ser un DOCX válido.")
        original_name = core.safe_filename(Path(filename).name)
        if not original_name.casefold().endswith(".docx"):
            raise ApprovalDeskError("El nombre de la revisión debe terminar en .docx.")
        with TemporaryDirectory(prefix="legalaiz-m325-") as temporary:
            target = Path(temporary) / original_name
            target.write_bytes(data)
            revision = self.desk.add_revision(
                case_id=desk_case_id,
                source_file=target,
                actor=_actor(user),
                note=str(note or "Revisión DOCX cargada desde la Mesa Jurídica.").strip(),
                parent_revision_id=detail["case"].get("current_revision_id"),
            )
''',
    '''        detected, digest, security_status = self.upload_validator(filename, data)
        if detected != "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            raise ApprovalDeskError("La revisión debe ser un DOCX válido.")
        actual_digest = sha256(data).hexdigest()
        if str(digest or "").casefold() != actual_digest:
            raise ApprovalDeskError("La huella del archivo no coincide con la validación de carga.")
        digest = actual_digest
        original_name = core.safe_filename(Path(filename).name)
        if not original_name.casefold().endswith(".docx"):
            raise ApprovalDeskError("El nombre de la revisión debe terminar en .docx.")
        base_note = str(note or "Revisión DOCX cargada desde la Mesa Jurídica.").strip()
        security_label = re.sub(r"[\\r\\n]+", " ", str(security_status or "unknown")).strip()[:200]
        persisted_note = (
            f"{base_note}\\n"
            f"[Validación M32.5: estado={security_label}; archivo={original_name}; sha256={digest}]"
        )
        with TemporaryDirectory(prefix="legalaiz-m325-") as temporary:
            target = Path(temporary) / original_name
            target.write_bytes(data)
            revision = self.desk.add_revision(
                case_id=desk_case_id,
                source_file=target,
                actor=_actor(user),
                note=persisted_note,
                parent_revision_id=detail["case"].get("current_revision_id"),
            )
''',
)

replace_exact(
    "legalai_platform/approval_desk_workspace.py",
    '''    def release(self, user: dict[str, Any], desk_case_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._authorize_case(user, desk_case_id)
        return self.desk.release(
''',
    '''    def release(self, user: dict[str, Any], desk_case_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        detail = self._authorize_case(user, desk_case_id)
        if not bool(detail.get("audit", {}).get("valid")):
            raise ReleaseBlocked("La cadena de auditoría no es íntegra; la liberación queda bloqueada.")
        return self.desk.release(
''',
)

replace_exact(
    "legalai_platform/approval_desk_workspace.py",
    '''        release = detail.get("release")
        if not release or detail.get("case", {}).get("status") != "released":
''',
    '''        if not bool(detail.get("audit", {}).get("valid")):
            raise ReleaseBlocked("La cadena de auditoría no es íntegra; la descarga liberada queda bloqueada.")
        release = detail.get("release")
        if not release or detail.get("case", {}).get("status") != "released":
''',
)

replace_exact(
    "legalai_platform/routes/m32_5_approval_desk_routes.py",
    '''    elif isinstance(exc, (ApprovalDeskError, ValueError, TypeError, KeyError, OSError)):
        handler.send_json({"error": str(exc)}, 422)
''',
    '''    elif isinstance(exc, (ApprovalDeskError, ValueError)):
        handler.send_json({"error": str(exc)}, 422)
''',
)

replace_exact(
    "app/modules/approval_desk_m32_5.js",
    '''  changes_required:'Requiere ajustes', rejected:'Rechazado', findings_pending:'Hallazgos pendientes',
  ready_to_release:'Listo para liberar', released:'Liberado',
''',
    '''  changes_required:'Requiere ajustes', rejected:'Rechazado', findings_pending:'Hallazgos pendientes',
  audit_invalid:'Cadena de auditoría inválida', ready_to_release:'Listo para liberar', released:'Liberado',
''',
)
replace_exact(
    "app/modules/approval_desk_m32_5.js",
    '''  draft:'neutral', legal_pending:'warning', qa_pending:'blue', changes_required:'danger', rejected:'danger',
  findings_pending:'warning', ready_to_release:'success', released:'success',
''',
    '''  draft:'neutral', legal_pending:'warning', qa_pending:'blue', changes_required:'danger', rejected:'danger',
  findings_pending:'warning', audit_invalid:'danger', ready_to_release:'success', released:'success',
''',
)

replace_exact(
    "tests/test_m32_5_approval_workspace.py",
    '''        self.assertEqual(revision["upload_sha256"], revision["sha256"])
        self.assertEqual(revision["filename"], "ajuste.docx")
''',
    '''        self.assertEqual(revision["upload_sha256"], revision["sha256"])
        self.assertEqual(revision["filename"], "ajuste.docx")
        detail = self.workspace.detail(self.legal, case_id)
        persisted_note = detail["revisions"][-1]["note"]
        self.assertIn("Validación M32.5", persisted_note)
        self.assertIn("clean:test", persisted_note)
        self.assertIn("ajuste.docx", persisted_note)
        self.assertIn(revision["sha256"], persisted_note)
''',
)

insertion = '''    def test_cadena_invalida_bloquea_liberacion(self):
        case_id = self.bootstrap()
        detail = self.workspace.detail(self.legal, case_id)
        current = detail["revisions"][0]
        self.workspace.approve(self.legal, case_id, {
            "revision_id": current["revision_id"],
            "approval_type": "legal",
            "decision": "approve",
            "comment": "Aprobación jurídica de prueba.",
            "expected_sha256": current["sha256"],
        })
        self.workspace.approve(self.admin, case_id, {
            "revision_id": current["revision_id"],
            "approval_type": "qa",
            "decision": "approve",
            "comment": "Aprobación QA de prueba.",
            "expected_sha256": current["sha256"],
        })
        events = self.workspace.root / case_id / "events.jsonl"
        lines = events.read_text(encoding="utf-8").splitlines()
        lines[0] = lines[0].replace('"case.created"', '"case.altered"')
        events.write_text("\\n".join(lines) + "\\n", encoding="utf-8")
        detail = self.workspace.detail(self.admin, case_id)
        self.assertFalse(detail["audit"]["valid"])
        self.assertEqual(detail["workflow_status"], "audit_invalid")
        with self.assertRaisesRegex(ReleaseBlocked, "cadena de auditoría"):
            self.workspace.release(self.admin, case_id, {
                "revision_id": current["revision_id"],
                "expected_sha256": current["sha256"],
            })

    def test_cadena_alterada_bloquea_descarga_ya_liberada(self):
        case_id = self.bootstrap()
        detail = self.workspace.detail(self.legal, case_id)
        current = detail["revisions"][0]
        for user, approval_type in ((self.legal, "legal"), (self.admin, "qa")):
            self.workspace.approve(user, case_id, {
                "revision_id": current["revision_id"],
                "approval_type": approval_type,
                "decision": "approve",
                "comment": f"Aprobación {approval_type} de prueba.",
                "expected_sha256": current["sha256"],
            })
        self.workspace.release(self.admin, case_id, {
            "revision_id": current["revision_id"],
            "expected_sha256": current["sha256"],
        })
        events = self.workspace.root / case_id / "events.jsonl"
        events.write_text(events.read_text(encoding="utf-8").replace('"document.released"', '"document.altered"'), encoding="utf-8")
        with self.assertRaisesRegex(ReleaseBlocked, "cadena de auditoría"):
            self.workspace.released_path(self.client, case_id)

'''
test_path = Path("tests/test_m32_5_approval_workspace.py")
test_text = test_path.read_text(encoding="utf-8")
marker = "\n\nclass ApprovalDeskStaticInterfaceM325Tests(TestCase):\n"
if marker not in test_text:
    raise SystemExit("No se encontró el punto de inserción de pruebas M32.5")
test_path.write_text(test_text.replace(marker, "\n\n" + insertion + "class ApprovalDeskStaticInterfaceM325Tests(TestCase):\n"), encoding="utf-8")

replace_exact(
    ".github/workflows/m32-5-approval-workspace.yml",
    '''        env:
          LEGAL_RUNTIME_DIR: ${{ runner.temp }}/m32-5-http-runtime
          LEGAL_ALLOW_DEMO_ACCOUNTS: "1"
          LEGAL_PORT: "8895"
        run: |
          python run.py --no-browser > "$RUNNER_TEMP/m32-5-server.log" 2>&1 &
          SERVER_PID=$!
          trap 'kill $SERVER_PID 2>/dev/null || true' EXIT
          for attempt in $(seq 1 60); do
            if curl -fsS http://127.0.0.1:8895/ >/dev/null; then break; fi
            sleep 1
          done
          curl -fsS http://127.0.0.1:8895/modules/approval_desk_m32_5.js >/dev/null
          curl -fsS http://127.0.0.1:8895/modules/approval_desk_m32_5.css >/dev/null
          STATUS=$(curl -sS -o "$RUNNER_TEMP/m32-5-unauthorized.json" -w '%{http_code}' http://127.0.0.1:8895/api/m32/approval-desk)
          test "$STATUS" = "401"
          grep -q 'Autenticación requerida' "$RUNNER_TEMP/m32-5-unauthorized.json"
''',
    '''        env:
          LEGAL_PROFILE: local
          LEGAL_APP_ENV: demo
          LEGAL_RUNTIME_DIR: ${{ runner.temp }}/m32-5-http-runtime
          LEGAL_ALLOW_DEMO_ACCOUNTS: "true"
          LEGAL_DEMO_PASSWORD: "LegalAIZDemo2026!"
          LEGAL_REQUIRE_MFA_ROLES: ""
          LEGAL_GITHUB_LITE_ASSETS: "true"
        run: |
          mkdir -p "$LEGAL_RUNTIME_DIR"
          python run.py 8895 --lan --no-browser > "$RUNNER_TEMP/m32-5-server.log" 2>&1 &
          SERVER_PID=$!
          trap 'kill $SERVER_PID 2>/dev/null || true' EXIT
          READY=0
          for attempt in $(seq 1 45); do
            if ! kill -0 "$SERVER_PID" 2>/dev/null; then
              cat "$RUNNER_TEMP/m32-5-server.log"
              exit 1
            fi
            if curl -fsS http://127.0.0.1:8895/api/live >/dev/null; then READY=1; break; fi
            sleep 1
          done
          if [ "$READY" != "1" ]; then cat "$RUNNER_TEMP/m32-5-server.log"; exit 1; fi
          curl -fsS http://127.0.0.1:8895/modules/approval_desk_m32_5.js >/dev/null
          curl -fsS http://127.0.0.1:8895/modules/approval_desk_m32_5.css >/dev/null
          STATUS=$(curl -sS -o "$RUNNER_TEMP/m32-5-unauthorized.json" -w '%{http_code}' http://127.0.0.1:8895/api/m32/approval-desk)
          test "$STATUS" = "401"
          grep -q 'Autenticación requerida' "$RUNNER_TEMP/m32-5-unauthorized.json"
''',
)

print("Parche M32.5 fail-closed aplicado.")
