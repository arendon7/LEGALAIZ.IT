from __future__ import annotations
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json

DEFAULT_RETENTION = {
    "anonymous_drafts_days": 30,
    "security_events_days": 365,
    "application_logs_days": 180,
    "inactive_sessions_days": 30,
    "rejected_upload_quarantine_days": 30,
    "closed_cases_days": 1825,
}

class PrivacyGovernance:
    def __init__(self, root: Path, settings):
        self.root=Path(root); self.settings=settings
        self.policy_path=self.root/'governance'/'m7'/'DATA_RETENTION_POLICY.json'

    def policy(self):
        if self.policy_path.is_file():
            try: return json.loads(self.policy_path.read_text(encoding='utf-8'))
            except Exception: pass
        return {"schema":"legalaizit-retention-v1","status":"draft","retention":DEFAULT_RETENTION}

    def inventory(self, con):
        tables={r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        targets={
            'users':'Identidad, rol y autenticación', 'cases':'Hechos y estado del expediente',
            'attachments':'Soportes y evidencias', 'documents':'Documentos jurídicos',
            'sessions':'Sesiones autenticadas', 'security_events':'Eventos de seguridad',
            'audit_log':'Trazabilidad de actuaciones', 'anonymous_drafts':'Borradores cifrados anónimos',
        }
        rows=[]
        for table,purpose in targets.items():
            if table in tables:
                count=con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                rows.append({"table":table,"purpose":purpose,"records":count})
        return rows

    def dry_run(self, con):
        policy=self.policy().get('retention',DEFAULT_RETENTION)
        now=datetime.now(timezone.utc)
        result=[]
        specs=[('sessions','last_seen_at',policy.get('inactive_sessions_days',30),"revoked=1"),('security_events','created_at',policy.get('security_events_days',365),"1=1")]
        tables={r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for table,column,days,extra in specs:
            if table not in tables: continue
            cutoff=(now-timedelta(days=int(days))).isoformat(timespec='seconds')
            count=con.execute(f"SELECT COUNT(*) FROM {table} WHERE {extra} AND {column}<?",(cutoff,)).fetchone()[0]
            result.append({"table":table,"cutoff":cutoff,"eligible_records":count,"action":"dry_run_only"})
        return {"policy_status":self.policy().get('status'),"items":result,"destructive_action_executed":False}
