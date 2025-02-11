from odoo.addons.esg.tests.esg_common import TestEsgCommon


class TestEsgEmissionFactor(TestEsgCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_gas_lines_emissions_value(self):
        self.assertEqual(self.computers_production_gas_lines[0].esg_emissions_value, 89.75)  # co2 line value = 89.75 (quantity) * 1 (GWP) = 89.75
        self.assertEqual(self.computers_production_gas_lines[1].esg_emissions_value, 0.42)  # ch4 line value = 0.02 (quantity) * 21 (GWP) = 0.42
        self.assertEqual(self.computers_production_gas_lines[2].esg_emissions_value, 3.1)  # n2o line value = 0.01 (quantity) * 310 (GWP) = 3.1

    def test_factor_emissions_value_with_gas_lines(self):
        self.assertEqual(self.emission_factor_computers_production.esg_emissions_value, 93.27)  # 89.75 (co2 line value) + 0.42 (ch4 line value) + 3.1 (n2o line value) = 93.27 kgCO2e / Unit
        self.computers_production_gas_lines[-1].unlink()
        self.assertEqual(self.emission_factor_computers_production.esg_emissions_value, 90.17)  # 89.75 (co2 line value) + 0.42 (ch4 line value) = 90.17 kgCO2e / Unit

    def test_factor_change_compute_method(self):
        # Initially, the compute method is physically
        self.assertEqual(self.emission_factor_computers_production.compute_method, 'physically')
        self.assertEqual(self.emission_factor_computers_production.uom_id, self.env.ref('uom.product_uom_unit'))
        # Let's change the compute method to monetary
        self.emission_factor_computers_production.compute_method = 'monetary'
        self.assertFalse(self.emission_factor_computers_production.uom_id)
        self.emission_factor_computers_production.currency_id = self.env.ref('base.USD')
        # Let's change it back to physically
        self.emission_factor_computers_production.compute_method = 'physically'
        self.assertFalse(self.emission_factor_computers_production.currency_id)
