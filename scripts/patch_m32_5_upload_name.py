from pathlib import Path

path = Path("legalai_platform/approval_desk_workspace.py")
text = path.read_text(encoding="utf-8")
old = '''        with TemporaryDirectory(prefix="legalaiz-m325-") as temporary:
            target = Path(temporary) / "revision.docx"
            target.write_bytes(data)
            revision = self.desk.add_revision(
                case_id=desk_case_id,
                source_file=target,
                actor=_actor(user),
                note=str(note or "Revisión DOCX cargada desde la Mesa Jurídica.").strip(),
                parent_revision_id=detail["case"].get("current_revision_id"),
            )
        revision["upload_sha256"] = digest
        revision["security_status"] = security_status
        revision["original_filename"] = Path(filename).name
        return revision
'''
new = '''        original_name = core.safe_filename(Path(filename).name)
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
        revision["upload_sha256"] = digest
        revision["security_status"] = security_status
        revision["original_filename"] = Path(filename).name
        return revision
'''
if old not in text:
    raise SystemExit("No se encontró el bloque exacto de carga que debía corregirse.")
path.write_text(text.replace(old, new), encoding="utf-8")
print("Nombre seguro de revisión DOCX aplicado.")
