from __future__ import annotations

"""Ciclo de entrega trazable de LegalAIZ.it v2.21.

Agrupa cambios cerrados de v2.20 en una versión candidata, congela el alcance
mediante hashes, hereda el cierre jurídico cuando no aplica, separa la
confirmación jurídica del QA técnico y produce un paquete de publicación
interna con evidencia inmutable.
"""

from datetime import datetime
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from typing import Any, Iterable
from zipfile import ZIP_DEFLATED, ZipFile
import json
import re
import uuid

VERSION = "2.21"
BASELINE_VERSION = "2.20"
RISK_RANK = {"low": 1, "medium": 2, "high": 3, "critical": 4}
SEMVER_RE = re.compile(r"^(\d+)\.(\d+)(?:\.(\d+))?(?:[-+][A-Za-z0-9.-]+)?$")


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha(value: Any) -> str:
    raw = value if isinstance(value, bytes) else _json(value).encode("utf-8")
    return sha256(raw).hexdigest()


def _decode_json(value: str | None, default: Any) -> Any:
    try:
        return json.loads(value or "")
    except Exception:
        return default


def _semver_tuple(value: str) -> tuple[int, int, int]:
    match = SEMVER_RE.match((value or "").strip())
    if not match:
        raise ValueError("La versión debe usar formato semántico, por ejemplo 2.21 o 2.21.1.")
    return tuple(int(x or 0) for x in match.groups())  # type: ignore[return-value]


class ReleaseCycleV221:
    def __init__(self, root: Path, change_control: Any):
        self.root = Path(root)
        self.change_control = change_control

    def create_schema(self, con) -> None:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS release_cycles_v221(
              id TEXT PRIMARY KEY,
              version TEXT NOT NULL UNIQUE,
              title TEXT NOT NULL,
              summary TEXT NOT NULL,
              baseline_version TEXT NOT NULL,
              status TEXT NOT NULL,
              change_set_ids_json TEXT NOT NULL,
              aggregate_paths_json TEXT NOT NULL,
              affected_components_json TEXT NOT NULL,
              inherited_components_json TEXT NOT NULL,
              impact_level TEXT NOT NULL,
              legal_scope_required INTEGER NOT NULL DEFAULT 0,
              snapshot_json TEXT NOT NULL,
              snapshot_sha256 TEXT NOT NULL,
              legal_status TEXT NOT NULL,
              legal_statement TEXT,
              legal_confirmed_by TEXT,
              legal_confirmed_at TEXT,
              qa_status TEXT NOT NULL,
              qa_statement TEXT,
              qa_confirmed_by TEXT,
              qa_confirmed_at TEXT,
              release_manifest_json TEXT,
              manifest_sha256 TEXT,
              created_by TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              published_by TEXT,
              published_at TEXT
            );
            CREATE TABLE IF NOT EXISTS release_events_v221(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              release_id TEXT NOT NULL,
              event_type TEXT NOT NULL,
              actor TEXT NOT NULL,
              actor_role TEXT NOT NULL,
              detail_json TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            """
        )

    def _event(self, con, release_id: str, event_type: str, user: dict[str, Any], detail: Any) -> None:
        con.execute(
            "INSERT INTO release_events_v221(release_id,event_type,actor,actor_role,detail_json,created_at) VALUES(?,?,?,?,?,?)",
            (release_id, event_type, user["id"], user["role"], _json(detail), _now()),
        )

    def _load(self, con, release_id: str):
        row = con.execute("SELECT * FROM release_cycles_v221 WHERE id=?", (release_id,)).fetchone()
        if not row:
            raise KeyError("Ciclo de entrega no encontrado.")
        return row

    def _decode(self, row: Any) -> dict[str, Any]:
        obj = dict(row)
        for key, default in (
            ("change_set_ids_json", []),
            ("aggregate_paths_json", []),
            ("affected_components_json", []),
            ("inherited_components_json", []),
            ("snapshot_json", {}),
            ("release_manifest_json", None),
        ):
            obj[key.replace("_json", "")] = _decode_json(obj.pop(key), default)
        obj["legal_scope_required"] = bool(obj["legal_scope_required"])
        return obj

    def _changes(self, con, ids: Iterable[str]) -> list[dict[str, Any]]:
        ordered = list(dict.fromkeys((x or "").strip() for x in ids if (x or "").strip()))
        if not ordered:
            raise ValueError("Debe vincular al menos un cambio cerrado.")
        if len(ordered) > 100:
            raise ValueError("Un ciclo admite máximo 100 cambios.")
        result: list[dict[str, Any]] = []
        for cid in ordered:
            try:
                detail = self.change_control.detail(con, cid)
            except KeyError as exc:
                raise ValueError(f"El cambio {cid} no existe.") from exc
            change = detail["change"]
            if change["status"] != "Cerrado":
                raise ValueError(f"El cambio {cid} todavía no está cerrado.")
            used = con.execute(
                "SELECT id,version FROM release_cycles_v221 WHERE status='Publicado' AND change_set_ids_json LIKE ?",
                (f'%"{cid}"%',),
            ).fetchone()
            if used:
                raise ValueError(f"El cambio {cid} ya fue publicado en la versión {used['version']}.")
            result.append(detail)
        return result

    def _snapshot(self, paths: Iterable[str]) -> dict[str, dict[str, Any]]:
        snapshot: dict[str, dict[str, Any]] = {}
        for rel in sorted(set(paths)):
            target = self.root / rel
            if target.is_file():
                snapshot[rel] = {"exists": True, "size": target.stat().st_size, "sha256": sha256(target.read_bytes()).hexdigest()}
            else:
                snapshot[rel] = {"exists": False, "size": 0, "sha256": ""}
        return snapshot

    def _drift(self, snapshot: dict[str, Any]) -> list[dict[str, Any]]:
        current = self._snapshot(snapshot.keys())
        rows: list[dict[str, Any]] = []
        for path in sorted(snapshot):
            before = snapshot[path]
            after = current[path]
            if before != after:
                rows.append({"path": path, "snapshot": before, "current": after})
        return rows

    def _aggregate(self, changes: list[dict[str, Any]]) -> dict[str, Any]:
        paths: set[str] = set()
        affected: set[str] = set()
        inherited_sets: list[set[str]] = []
        legal_required = False
        risk = "low"
        summaries: list[dict[str, Any]] = []
        for detail in changes:
            c = detail["change"]
            paths.update(c.get("declared_paths") or [])
            affected.update(c.get("affected_components") or [])
            inherited_sets.append(set(c.get("inherited_components") or []))
            legal_required = legal_required or bool(c.get("legal_signoff_required"))
            if RISK_RANK.get(c.get("impact_level", "low"), 1) > RISK_RANK.get(risk, 1):
                risk = c.get("impact_level", "low")
            summaries.append({
                "id": c["id"], "title": c["title"], "status": c["status"],
                "impact_level": c["impact_level"], "plan_sha256": c["plan_sha256"],
                "legal_signoff_required": bool(c["legal_signoff_required"]),
                "closed_at": c.get("closed_at"),
            })
        inherited = set.intersection(*inherited_sets) if inherited_sets else set()
        inherited.difference_update(affected)
        return {
            "paths": sorted(paths),
            "affected_components": sorted(affected),
            "inherited_components": sorted(inherited),
            "impact_level": risk,
            "legal_scope_required": legal_required,
            "changes": summaries,
        }

    def create_release(
        self, con, user: dict[str, Any], version: str, title: str, summary: str,
        change_set_ids: Iterable[str],
    ) -> dict[str, Any]:
        self.create_schema(con)
        if user.get("role") not in {"specialist", "admin"}:
            raise PermissionError("Solo el abogado responsable o administración pueden proponer una entrega.")
        version = (version or "").strip()
        if _semver_tuple(version) <= _semver_tuple(BASELINE_VERSION):
            raise ValueError(f"La versión objetivo debe ser posterior a {BASELINE_VERSION}.")
        title = (title or "").strip()
        if len(title) < 5:
            raise ValueError("La entrega requiere un título descriptivo.")
        changes = self._changes(con, change_set_ids)
        aggregate = self._aggregate(changes)
        snapshot = self._snapshot(aggregate["paths"])
        rid = "REL-" + uuid.uuid4().hex[:10].upper()
        now = _now()
        legal_status = "pending" if aggregate["legal_scope_required"] else "inherited"
        try:
            con.execute(
                """INSERT INTO release_cycles_v221(
                  id,version,title,summary,baseline_version,status,change_set_ids_json,
                  aggregate_paths_json,affected_components_json,inherited_components_json,
                  impact_level,legal_scope_required,snapshot_json,snapshot_sha256,
                  legal_status,qa_status,created_by,created_at,updated_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    rid, version, title[:240], (summary or "").strip()[:4000], BASELINE_VERSION, "En revisión",
                    _json([x["change"]["id"] for x in changes]), _json(aggregate["paths"]),
                    _json(aggregate["affected_components"]), _json(aggregate["inherited_components"]),
                    aggregate["impact_level"], int(aggregate["legal_scope_required"]), _json(snapshot), _sha(snapshot),
                    legal_status, "pending", user["id"], now, now,
                ),
            )
        except Exception as exc:
            if "UNIQUE" in str(exc).upper():
                raise ValueError("Ya existe un ciclo con esa versión.") from exc
            raise
        self._event(con, rid, "release_proposed", user, {
            "version": version, "change_set_ids": [x["change"]["id"] for x in changes],
            "snapshot_sha256": _sha(snapshot), "legal_scope_required": aggregate["legal_scope_required"],
        })
        return self.detail(con, rid)

    def _readiness(self, obj: dict[str, Any], drift: list[dict[str, Any]], linked_changes: list[dict[str, Any]]) -> dict[str, Any]:
        all_changes_closed = all(x["change"]["status"] == "Cerrado" for x in linked_changes)
        legal_ready = (not obj["legal_scope_required"]) or obj["legal_status"] == "confirmed"
        qa_ready = obj["qa_status"] == "confirmed"
        no_drift = not drift
        published = obj["status"] == "Publicado"
        return {
            "all_changes_closed": all_changes_closed,
            "legal_ready": legal_ready,
            "qa_ready": qa_ready,
            "no_drift": no_drift,
            "drift_count": len(drift),
            "ready_for_legal": obj["legal_scope_required"] and all_changes_closed and no_drift and not published,
            "ready_for_qa": all_changes_closed and legal_ready and no_drift and not published,
            "ready_to_publish": all_changes_closed and legal_ready and qa_ready and no_drift and not published,
            "published": published,
        }

    def detail(self, con, release_id: str) -> dict[str, Any]:
        obj = self._decode(self._load(con, release_id))
        linked: list[dict[str, Any]] = []
        for cid in obj["change_set_ids"]:
            linked.append(self.change_control.detail(con, cid))
        drift = self._drift(obj["snapshot"])
        readiness = self._readiness(obj, drift, linked)
        effective_status = "Requiere actualización" if drift and obj["status"] != "Publicado" else obj["status"]
        events = [dict(x) for x in con.execute(
            "SELECT * FROM release_events_v221 WHERE release_id=? ORDER BY id DESC LIMIT 150", (release_id,)
        ).fetchall()]
        return {
            "release": {**obj, "effective_status": effective_status},
            "linked_changes": [x["change"] for x in linked],
            "drift": drift,
            "readiness": readiness,
            "events": events,
        }

    def confirm_legal(self, con, user: dict[str, Any], release_id: str, statement: str) -> dict[str, Any]:
        self.create_schema(con)
        row = self._decode(self._load(con, release_id))
        if user.get("role") != "specialist":
            raise PermissionError("La confirmación del alcance jurídico corresponde al abogado responsable.")
        if row["status"] == "Publicado":
            raise ValueError("La entrega publicada es inmutable.")
        if not row["legal_scope_required"]:
            raise ValueError("Esta entrega no reabre el cierre jurídico; la evidencia se hereda.")
        detail = self.detail(con, release_id)
        if detail["drift"]:
            raise ValueError("Existen cambios posteriores al snapshot. Rebase la entrega antes de aprobar.")
        statement = (statement or "").strip()
        if len(statement) < 12:
            raise ValueError("Registre una declaración jurídica suficientemente descriptiva.")
        now = _now()
        con.execute(
            """UPDATE release_cycles_v221 SET legal_status='confirmed',legal_statement=?,
               legal_confirmed_by=?,legal_confirmed_at=?,qa_status='pending',qa_statement=NULL,
               qa_confirmed_by=NULL,qa_confirmed_at=NULL,status='En revisión',updated_at=? WHERE id=?""",
            (statement[:4000], user["id"], now, now, release_id),
        )
        self._event(con, release_id, "legal_scope_confirmed", user, {"statement_sha256": _sha(statement)})
        return self.detail(con, release_id)

    def confirm_qa(self, con, user: dict[str, Any], release_id: str, statement: str) -> dict[str, Any]:
        self.create_schema(con)
        row = self._decode(self._load(con, release_id))
        if user.get("role") != "admin":
            raise PermissionError("La confirmación QA corresponde a administración.")
        if row["status"] == "Publicado":
            raise ValueError("La entrega publicada es inmutable.")
        detail = self.detail(con, release_id)
        if not detail["readiness"]["ready_for_qa"]:
            if detail["drift"]:
                raise ValueError("Existen cambios posteriores al snapshot. Rebase la entrega antes del QA.")
            raise ValueError("El alcance jurídico o los cambios vinculados todavía no están listos.")
        statement = (statement or "").strip()
        if len(statement) < 12:
            raise ValueError("Registre una declaración QA suficientemente descriptiva.")
        now = _now()
        con.execute(
            """UPDATE release_cycles_v221 SET qa_status='confirmed',qa_statement=?,qa_confirmed_by=?,
               qa_confirmed_at=?,status='Listo para publicar',updated_at=? WHERE id=?""",
            (statement[:4000], user["id"], now, now, release_id),
        )
        self._event(con, release_id, "qa_confirmed", user, {"statement_sha256": _sha(statement)})
        return self.detail(con, release_id)

    def rebase(self, con, user: dict[str, Any], release_id: str) -> dict[str, Any]:
        self.create_schema(con)
        row = self._decode(self._load(con, release_id))
        if user.get("role") != "admin":
            raise PermissionError("El rebase del snapshot corresponde a administración.")
        if row["status"] == "Publicado":
            raise ValueError("La entrega publicada es inmutable.")
        linked = self._changes(con, row["change_set_ids"])
        aggregate = self._aggregate(linked)
        snapshot = self._snapshot(aggregate["paths"])
        legal_status = "pending" if aggregate["legal_scope_required"] else "inherited"
        now = _now()
        con.execute(
            """UPDATE release_cycles_v221 SET aggregate_paths_json=?,affected_components_json=?,
               inherited_components_json=?,impact_level=?,legal_scope_required=?,snapshot_json=?,snapshot_sha256=?,
               legal_status=?,legal_statement=NULL,legal_confirmed_by=NULL,legal_confirmed_at=NULL,
               qa_status='pending',qa_statement=NULL,qa_confirmed_by=NULL,qa_confirmed_at=NULL,
               release_manifest_json=NULL,manifest_sha256=NULL,status='En revisión',updated_at=? WHERE id=?""",
            (
                _json(aggregate["paths"]), _json(aggregate["affected_components"]),
                _json(aggregate["inherited_components"]), aggregate["impact_level"],
                int(aggregate["legal_scope_required"]), _json(snapshot), _sha(snapshot),
                legal_status, now, release_id,
            ),
        )
        self._event(con, release_id, "snapshot_rebased", user, {"snapshot_sha256": _sha(snapshot), "paths": len(snapshot)})
        return self.detail(con, release_id)

    def _manifest(self, con, row: dict[str, Any]) -> dict[str, Any]:
        details = [self.change_control.detail(con, cid) for cid in row["change_set_ids"]]
        return {
            "schema": "legalaiz.release.v221",
            "release_id": row["id"],
            "version": row["version"],
            "baseline_version": row["baseline_version"],
            "title": row["title"],
            "summary": row["summary"],
            "impact_level": row["impact_level"],
            "legal_scope_required": row["legal_scope_required"],
            "legal_status": row["legal_status"],
            "legal_confirmed_by": row.get("legal_confirmed_by"),
            "legal_confirmed_at": row.get("legal_confirmed_at"),
            "qa_status": row["qa_status"],
            "qa_confirmed_by": row.get("qa_confirmed_by"),
            "qa_confirmed_at": row.get("qa_confirmed_at"),
            "snapshot_sha256": row["snapshot_sha256"],
            "files": row["snapshot"],
            "affected_components": row["affected_components"],
            "inherited_components": row["inherited_components"],
            "changes": [
                {
                    "id": x["change"]["id"], "title": x["change"]["title"],
                    "plan_sha256": x["change"]["plan_sha256"], "closed_at": x["change"].get("closed_at"),
                    "evidence_sha256": _sha(json.loads(self.change_control.evidence(con, x["change"]["id"]))),
                }
                for x in details
            ],
            "publication_scope": "Piloto interno controlado; no equivale a firma, publicación profesional ni despliegue productivo.",
        }

    def publish(self, con, user: dict[str, Any], release_id: str) -> dict[str, Any]:
        self.create_schema(con)
        row = self._decode(self._load(con, release_id))
        if user.get("role") != "admin":
            raise PermissionError("La publicación interna corresponde a administración.")
        if row["status"] == "Publicado":
            return self.detail(con, release_id)
        detail = self.detail(con, release_id)
        if not detail["readiness"]["ready_to_publish"]:
            raise ValueError("La entrega no cumple las condiciones de publicación.")
        manifest = self._manifest(con, row)
        manifest["published_at"] = _now()
        manifest["published_by"] = user["id"]
        manifest_sha = _sha(manifest)
        manifest["manifest_sha256"] = manifest_sha
        now = manifest["published_at"]
        con.execute(
            """UPDATE release_cycles_v221 SET status='Publicado',release_manifest_json=?,manifest_sha256=?,
               published_by=?,published_at=?,updated_at=? WHERE id=?""",
            (_json(manifest), manifest_sha, user["id"], now, now, release_id),
        )
        self._event(con, release_id, "release_published", user, {"version": row["version"], "manifest_sha256": manifest_sha})
        return self.detail(con, release_id)

    def summary(self, con) -> dict[str, Any]:
        self.create_schema(con)
        rows = [self._decode(x) for x in con.execute(
            "SELECT * FROM release_cycles_v221 ORDER BY created_at DESC LIMIT 60"
        ).fetchall()]
        closed_changes = [dict(x) for x in con.execute(
            """SELECT id,title,summary,impact_level,legal_signoff_required,closed_at,target_version
               FROM change_sets_v220 WHERE status='Cerrado' ORDER BY closed_at DESC LIMIT 100"""
        ).fetchall()]
        published_ids: set[str] = set()
        for row in rows:
            if row["status"] == "Publicado":
                published_ids.update(row["change_set_ids"])
        for change in closed_changes:
            change["legal_signoff_required"] = bool(change["legal_signoff_required"])
            change["available"] = change["id"] not in published_ids
        return {
            "version": VERSION,
            "baseline_version": BASELINE_VERSION,
            "title": "Ciclo de entrega trazable",
            "releases": rows,
            "available_changes": closed_changes,
            "metrics": {
                "release_candidates": len(rows),
                "in_review": sum(x["status"] != "Publicado" for x in rows),
                "published": sum(x["status"] == "Publicado" for x in rows),
                "closed_changes_available": sum(bool(x["available"]) for x in closed_changes),
            },
            "operating_rule": (
                "Cada versión agrupa cambios cerrados, congela sus archivos mediante SHA-256 y conserva las aprobaciones "
                "del alcance exacto. El cierre jurídico solo se solicita si algún cambio modificó contenido jurídico."
            ),
        }

    def evidence(self, con, release_id: str) -> bytes:
        obj = self.detail(con, release_id)
        obj["exported_at"] = _now()
        obj["evidence_sha256"] = _sha(obj)
        return json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")

    def bundle(self, con, release_id: str) -> bytes:
        detail = self.detail(con, release_id)
        row = detail["release"]
        if row["status"] != "Publicado" or not row.get("release_manifest"):
            raise ValueError("El paquete solo está disponible después de la publicación interna.")
        out = BytesIO()
        with ZipFile(out, "w", ZIP_DEFLATED) as zf:
            manifest = json.dumps(row["release_manifest"], ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
            zf.writestr("MANIFEST_RELEASE.json", manifest)
            zf.writestr("EVIDENCIA_CICLO.json", self.evidence(con, release_id))
            for cid in row["change_set_ids"]:
                zf.writestr(f"cambios/{cid}_evidencia.json", self.change_control.evidence(con, cid))
            zf.writestr(
                "LEEME.txt",
                (
                    f"LegalAIZ.it {row['version']} — paquete de evidencia de publicación interna\n"
                    f"Release: {row['id']}\nManifest SHA-256: {row['manifest_sha256']}\n\n"
                    "Este paquete acredita el ciclo interno de cambios, validación y publicación. "
                    "No autoriza por sí solo firma, uso profesional ni despliegue productivo.\n"
                ).encode("utf-8"),
            )
        return out.getvalue()
