# M35.2 — Security boundary

- No se aceptan pagos reales.
- Un handoff M35 activo bloquea la creación de órdenes genéricas para ese usuario/producto.
- Las órdenes M35.2 bloquean `pay_order` legacy.
- La creación genérica de casos queda bloqueada cuando existe una continuidad M35 activa.
- Sólo un payment intent sandbox firmado y vinculado puede autorizar `finalize`.
- Cambios del draft, orden, precio o riesgo después del checkout bloquean el expediente.
- Los valores jurídicos no se copian al ledger ni a observabilidad.
