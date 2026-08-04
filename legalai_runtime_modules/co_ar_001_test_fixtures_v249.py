def complete_answers():
    return {
        "lease": {"configuration": "joint"},
        "landlord": {
            "identification": {"type": "legal", "name": "Arrendamientos Ejemplo S.A.S.", "id_number": "901.000.001-1", "address": "Medellín", "email": "arrendador@example.com", "phone": "3000000000"},
            "signatory": {"name": "Ana Representante", "id_number": "43.000.001", "capacity": "representante legal", "authority_source": "certificado de existencia y representación"},
            "authority_evidence": "owner",
        },
        "tenant": {
            "identification": {"type": "natural", "name": "Carlos Arrendatario", "id_number": "71.000.001", "address": "Medellín", "email": "tenant@example.com", "phone": "3100000000"},
            "additional": {"names": "María Arrendataria, CC 43.000.002", "solidarity": "yes"},
        },
        "notifications": {"channels": {"landlord_channel": "arrendador@example.com", "tenant_channel": "tenant@example.com", "physical_addresses": "Medellín, Antioquia"}},
        "scope": {"urban_home": "yes"},
        "property": {
            "identification": {"address": "Calle 10 # 20-30, apto. 501", "municipality": "Medellín, Antioquia", "registration": "001-123456", "cadastral_id": "05001-01-0001"},
            "type": "apartment",
            "included_units": {"private_area": "Apartamento 501", "parking": "Parqueadero 18", "storage": "Cuarto útil 7", "other": "Uso de zonas comunes conforme al reglamento"},
            "horizontal": True,
            "ph_details": {"name": "Edificio Ejemplo P.H.", "administrator": "Administración Ejemplo", "rules_delivery": "yes", "ordinary_fee": 350000},
            "dispute_status": "none",
            "furnished": True,
            "high_value_assets": True,
        },
        "use": {"destination": "residential_remote", "sublease_tourism": "none", "shared_areas": "Gimnasio y salón social conforme al reglamento"},
        "occupants": {"authorized": "Carlos y María", "multiple": True},
        "pets": {"exists": True, "conditions": "Una mascota doméstica, con manejo responsable y reparación de daños comprobados."},
        "condition": {"habitability": "fit", "defects": "Rayón menor en puerta de estudio.", "repairs_pending": {"items": "Ajuste de una bisagra", "responsible": "Arrendador dentro de los cinco días siguientes"}},
        "delivery": {"inventory_method": "combined", "date": "2026-08-01"},
        "maintenance": {"rules": {"routine": "Mantenimiento ordinario y reparaciones locativas imputables al uso.", "improvements": "Requieren autorización escrita.", "authorization": "Solicitud por correo con alcance y reversibilidad."}},
        "rent": {"amount": 2500000, "values": {"commercial_value": 350000000, "cadastral_value": 200000000, "source_date": "Avalúo comercial de julio de 2026"}, "payment": {"frequency": "monthly", "day": 5, "method": "transferencia", "account": "Cuenta informada por el arrendador"}, "adjustment": "legal_ipc"},
        "charges": {"additional_services": {"exists": True, "description": "Internet administrado", "value": 150000}, "administration": {"ordinary_amount": 350000, "ordinary_responsible": "tenant", "extraordinary_responsible": "landlord"}, "utilities": {"responsible": "special", "distribution": "Según medidores individuales y facturas", "internet": "Incluido como servicio adicional", "gas_or_other": "Gas según factura"}},
        "utilities": {"denunciation": "yes"},
        "guarantee": {"type": "policy", "details": {"party": "Aseguradora Ejemplo S.A.", "id_number": "PÓL-2026-001", "scope": "Canon, servicios y daños comprobados dentro de la póliza", "validity": "Durante el contrato y sus prórrogas"}, "cash_deposit": False},
        "term": {"duration_months": 12, "rules": {"automatic_extension": "yes", "notice_days": 90, "special_termination": "Ocupación del propietario, sujeta a requisitos legales"}},
        "data": {"screening": {"credit_study": True, "personal_data": "Estudio, celebración, ejecución, cobranza y cierre contractual", "sensitive_documents": False}},
        "confirmation": {"reviewed": True},
    }

