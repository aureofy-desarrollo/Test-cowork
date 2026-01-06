from odoo.tests.common import TransactionCase, tagged
from odoo import fields

@tagged('post_install', '-at_install')
class TestCreditsPurchase(TransactionCase):

    def setUp(self):
        super(TestCreditsPurchase, self).setUp()
        self.partner = self.env['res.partner'].create({'name': 'Test Partner'})
        self.product_credits = self.env.ref('aureofy_cowork_ll.product_credits')
        self.product_credits.list_price = 10.0

    def test_purchase_credits_via_sale_order(self):
        """Test that confirming a sale order grants credits"""
        # Create Sale Order
        so = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {
                'product_id': self.product_credits.id,
                'product_uom_qty': 5,
                'price_unit': 10.0,
            })]
        })
        
        # Confirm Sale Order
        so.action_confirm()
        
        # Check credits
        credits = self.env['cowork.credits'].search([
            ('partner_id', '=', self.partner.id),
            ('sale_id', '=', so.id)
        ])
        
        self.assertTrue(credits, "Credits record should be created")
        self.assertEqual(credits.credits_amount, 5, "Should verify 5 credits granted")
        self.assertEqual(credits.credits_type, 'purchased', "Type should be purchased")
        self.assertEqual(credits.price_per_credit, 10.0, "Price per credit should match")

    def test_pricelist_integration(self):
        """Test that pricelists affect the credit price (standard Odoo, but verifying flow)"""
        pricelist = self.env['product.pricelist'].create({
            'name': 'Discount Pricelist',
            'item_ids': [(0, 0, {
                'applied_on': '1_product',
                'product_tmpl_id': self.product_credits.product_tmpl_id.id,
                'min_quantity': 10,
                'compute_price': 'fixed',
                'fixed_price': 8.0,
            })]
        })
        
        so = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'pricelist_id': pricelist.id,
            'order_line': [(0, 0, {
                'product_id': self.product_credits.id,
                'product_uom_qty': 10,
            })]
        })
        
        # Odoo recomputes onchain, but explicitly triggering helps in tests sometimes or just checking result
        # In test execution, onchange might not trigger automatically unless using Form
        # But create should respect defaults if passed, here we depend on pricelist logic which happens on creation/write if configured
        # Let's force price update to simulate UI behavior or standard flow
        so.order_line._compute_price_unit()
        
        self.assertEqual(so.order_line.price_unit, 8.0, "Pricelist should apply 8.0 price")
        
        so.action_confirm()
        
        credits = self.env['cowork.credits'].search([
            ('partner_id', '=', self.partner.id),
            ('sale_id', '=', so.id)
        ])
        
        self.assertEqual(credits.price_per_credit, 8.0, "Credits should record the discounted price")
