from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from co_la_002_document_factory_v239 import CoLa002DocumentFactoryV239
from m33_document_presentation import (
    APPROVAL_CANDIDATE_MODE,
    audit_m33_presentation,
    build_m33_presentation,
)
from m33_employment_instrument_finalize import compose_employment_m33_instrument


class CoLa002DocumentFactoryV240(CoLa002DocumentFactoryV239):
    """CO-LA-002 M33.0: conserva paquete v2.39 y recompone solo el contrato principal."""

    VERSION = "2.40"
    DOCUMENT_STANDARD = "M33.0"

    def __init__(self, root: Path, evaluator):
        super().__init__(root, evaluator)
        self.output_dir = Path(root) / "data" / "generated" / "co-la-002-v240"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._m33_review_evidence: dict[str, dict] = {}

    @staticmethod
    def _cover_subtitle(answers: dict) -> str:
        employer = answers.get("employer") if isinstance(answers.get("employer"), dict) else {}
        worker = answers.get("worker") if isinstance(answers.get("worker"), dict) else {}
        work = answers.get("work") if isinstance(answers.get("work"), dict) else {}
        employer_name = str(employer.get("legalName") or employer.get("naturalPersonFullName") or "EL EMPLEADOR")
        worker_name = str(worker.get("fullName") or "LA PERSONA TRABAJADORA")
        place = str(work.get("mainWorkplace") or "").strip()
        start = CoLa002DocumentFactoryV239._date_es(work.get("actualStartDate"))
        context = f"{employer_name} · {worker_name}"
        location_date = " · ".join(value for value in (place, start) if value)
        return f"{context}\n{location_date}" if location_date else context

    @staticmethod
    def _format_nit(value) -> str:
        """Formatea el NIT para lectura humana sin modificar el dato canónico de entrada."""
        text = str(value or "").strip()
        match = re.fullmatch(r"(\d{7,12})(?:-(\d))?", text)
        if not match:
            return text
        base, check_digit = match.groups()
        groups = []
        while base:
            groups.append(base[-3:])
            base = base[:-3]
        formatted = ".".join(reversed(groups))
        return f"{formatted}-{check_digit}" if check_digit else formatted

    @classmethod
    def _normalize_render_identifiers(cls, value, raw_nit: str, formatted_nit: str):
        """Sustituye únicamente la representación visible del NIT dentro de la composición."""
        if isinstance(value, str):
            return value.replace(raw_nit, formatted_nit) if raw_nit and formatted_nit else value
        if isinstance(value, list):
            return [cls._normalize_render_identifiers(item, raw_nit, formatted_nit) for item in value]
        if isinstance(value, tuple):
            return tuple(cls._normalize_render_identifiers(item, raw_nit, formatted_nit) for item in value)
        if isinstance(value, dict):
            return {
                key: cls._normalize_render_identifiers(item, raw_nit, formatted_nit)
                for key, item in value.items()
            }
        return value

    def _contract(self, answers: dict, evaluation: dict, target: Path):
        composition = compose_employment_m33_instrument(answers)
        employer = answers.get("employer") if isinstance(answers.get("employer"), dict) else {}
        worker = answers.get("worker") if isinstance(answers.get("worker"), dict) else {}

        raw_nit = str(employer.get("identificationNumber") or "").strip()
        formatted_nit = self._format_nit(raw_nit)
        if raw_nit and formatted_nit != raw_nit:
            composition["sections"] = self._normalize_render_identifiers(
                composition.get("sections") or [], raw_nit, formatted_nit
            )

        evidence = build_m33_presentation(
            path=target,
            title=composition["title"],
            subtitle=composition.get("subtitle") or "",
            metadata=[
                ("Producto", "CO-LA-002"),
                ("Empleador", str(employer.get("legalName") or employer.get("naturalPersonFullName") or "Empleador")),
                ("Persona trabajadora", str(worker.get("fullName") or "Persona trabajadora")),
                ("Estándar documental", self.DOCUMENT_STANDARD),
                ("Estado", "Candidato sujeto a revisión jurídica y QA"),
            ],
            sections=composition["sections"],
            product_code="CO-LA-002",
            presentation_mode=APPROVAL_CANDIDATE_MODE,
            approval_subtitle=self._cover_subtitle(answers),
        )
        self._m33_review_evidence[target.name] = evidence

    def generate(self, answers, actor=None):
        manifest = super().generate(answers, actor=actor)
        manifest["version"] = self.VERSION
        manifest["document_standard"] = self.DOCUMENT_STANDARD
        manifest["status"] = "draft_generated"
        manifest["released"] = False

        folder = self.output_dir / manifest["generation_id"]
        primary = next((item for item in manifest.get("documents", []) if item.get("id") == "DOC-LA-CONTRACT-001"), None)
        if not primary:
            raise RuntimeError("CO-LA-002 M33.0 no encontró el contrato principal generado.")
        primary_path = folder / primary["filename"]
        standard = audit_m33_presentation(primary_path, APPROVAL_CANDIDATE_MODE)
        if not standard["valid"]:
            raise ValueError(f"CO-LA-002 no supera el estándar M33.0: {standard['findings']}")
        primary["document_standard"] = self.DOCUMENT_STANDARD
        primary["presentation_mode"] = APPROVAL_CANDIDATE_MODE
        primary["review_evidence"] = self._m33_review_evidence.get(primary["filename"], {})
        primary["approval_state"] = {"legal": "pending", "qa": "pending"}
        primary["release_rule"] = "Liberar únicamente el mismo SHA-256 aprobado por Jurídico y QA."
        primary["m33_preflight"] = standard

        # Reescribe el manifiesto versionado y recompone el ZIP para que la evidencia
        # descargable corresponda a la fábrica M33.0, sin alterar el esquema histórico.
        manifest_path = folder / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        package = self.output_dir / f"{manifest['generation_id']}.zip"
        with ZipFile(package, "w", ZIP_DEFLATED) as archive:
            for path in sorted(folder.iterdir()):
                if path.is_file():
                    archive.write(path, arcname=path.name)
        manifest["package_filename"] = package.name
        manifest["package_sha256"] = hashlib.sha256(package.read_bytes()).hexdigest()
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return manifest
