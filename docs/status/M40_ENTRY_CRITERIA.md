# M40 — Entry Criteria

M40.0 puede comenzar cuando:

1. M39.2 tenga un SHA exacto certificado.
2. La pila M38/M39 esté identificada y sin ambigüedad de fuente canónica.
3. No existan eliminaciones pendientes que puedan afectar imports/runtime de M40.
4. El inventario de limpieza distinga activos, compatibilidad, tooling y candidatos.
5. El piso 11 productos + fábrica documental + M34–M39 permanezca verde.

## Gate arquitectónico
M40 debe añadirse de forma incremental. Ningún proveedor/modelo puede:
- promover hechos no confirmados;
- saltarse RBAC/tenant isolation;
- sobrescribir revisiones aprobadas;
- aprobar Legal o QA;
- exponer payload sensible en observabilidad;
- activar pagos o producción por sí mismo.
