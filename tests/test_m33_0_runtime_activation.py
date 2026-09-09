from __future__ import annotations

import unittest


class RuntimeActivationM330Tests(unittest.TestCase):
    def test_run_activates_m33_contract_factories_without_deleting_historical_classes(self):
        import run
        from co_ar_001_document_factory_v250 import CoAr001DocumentFactoryV250
        from co_em_003_document_factory_v244 import CoEm003DocumentFactoryV244
        from co_em_004_document_factory_v247 import CoEm004DocumentFactoryV247
        from co_la_002_document_factory_v239 import CoLa002DocumentFactoryV239

        self.assertEqual(type(run.COEM003_FACTORY_V244).__name__, "CoEm003DocumentFactoryV245")
        self.assertEqual(type(run.COEM004_FACTORY_V247).__name__, "CoEm004DocumentFactoryV248")
        self.assertEqual(type(run.COAR001_FACTORY_V250).__name__, "CoAr001DocumentFactoryV251")
        self.assertEqual(type(run.COLA002_FACTORY_V239).__name__, "CoLa002DocumentFactoryV240")

        self.assertEqual(run.COEM003_FACTORY_V244.VERSION, "2.45")
        self.assertEqual(run.COEM004_FACTORY_V247.VERSION, "2.48")
        self.assertEqual(run.COAR001_FACTORY_V250.VERSION, "2.51")
        self.assertEqual(run.COLA002_FACTORY_V239.VERSION, "2.40")

        # Los servicios que consume el Handler deben apuntar a las mismas instancias.
        services = run._application_services
        self.assertIs(services.COEM003_FACTORY_V244, run.COEM003_FACTORY_V244)
        self.assertIs(services.COEM004_FACTORY_V247, run.COEM004_FACTORY_V247)
        self.assertIs(services.COAR001_FACTORY_V250, run.COAR001_FACTORY_V250)
        self.assertIs(services.COLA002_FACTORY_V239, run.COLA002_FACTORY_V239)

        # Las clases históricas continúan disponibles para regresión y comparación.
        self.assertEqual(CoEm003DocumentFactoryV244.VERSION, "2.44")
        self.assertEqual(CoEm004DocumentFactoryV247.VERSION, "2.47")
        self.assertEqual(CoAr001DocumentFactoryV250.VERSION, "2.50")
        # v2.39 laboral era anterior a la convención VERSION; lo importante es que
        # siga siendo la clase histórica y no haya recibido marcadores M33.
        self.assertEqual(CoLa002DocumentFactoryV239.__name__, "CoLa002DocumentFactoryV239")
        self.assertFalse(hasattr(CoLa002DocumentFactoryV239, "DOCUMENT_STANDARD"))

        # La gobernanza activa también debe corresponder al nuevo directorio/versionado.
        self.assertIs(run.COEM003_GOVERNANCE_V244.factory, run.COEM003_FACTORY_V244)
        self.assertIs(run.COEM004_GOVERNANCE_V247.factory, run.COEM004_FACTORY_V247)
        self.assertIs(run.COAR001_GOVERNANCE_V250.factory, run.COAR001_FACTORY_V250)
        self.assertIs(run.COLA002_GOVERNANCE_V240.factory, run.COLA002_FACTORY_V239)


if __name__ == "__main__":
    unittest.main()
