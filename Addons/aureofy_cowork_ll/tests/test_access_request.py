# -*- coding: utf-8 -*-

from odoo.tests import TransactionCase
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta

class TestAccessRequest(TransactionCase):

    def setUp(self):
        super(TestAccessRequest, self).setUp()
        self.partner = self.env['res.partner'].create({'name': 'Test Partner'})
        self.membership_plan = self.env['cowork.membership.plan'].create({
            'name': 'Test Plan',
            'price': 100.0,
        })
        self.membership = self.env['cowork.membership'].create({
            'partner_id': self.partner.id,
            'plan_id': self.membership_plan.id,
            'date_start': datetime.now(),
        })
        self.service = self.env['cowork.service'].create({
            'name': 'Test Service',
            'is_paid': True,
            'price': 50.0,
            'service_type': 'meeting_room',
        })
        self.AccessRequest = self.env['cowork.access.request']

    def test_dynamic_price(self):
        """Test that price is computed based on duration"""
        request = self.AccessRequest.create({
            'membership_id': self.membership.id,
            'service_id': self.service.id,
            'date_scheduled': datetime.now(),
            'duration_hours': 1.0,
        })
        self.assertEqual(request.price, 50.0, "Price should be 50 for 1 hour")

        request.duration_hours = 2.0
        self.assertEqual(request.price, 100.0, "Price should be 100 for 2 hours")

        request.duration_hours = 0.5
        self.assertEqual(request.price, 25.0, "Price should be 25 for 0.5 hours")

    def test_dynamic_credits(self):
        """Test that credit cost is computed based on duration"""
        # Set credit cost on service
        self.service.credits_cost = 10
        
        request = self.AccessRequest.create({
            'membership_id': self.membership.id,
            'service_id': self.service.id,
            'date_scheduled': datetime.now(),
            'duration_hours': 1.0,
        })
        self.assertEqual(request.credits_cost, 10, "Credits should be 10 for 1 hour")

        request.duration_hours = 2.0
        self.assertEqual(request.credits_cost, 20, "Credits should be 20 for 2 hours")

        request.duration_hours = 0.5
        self.assertEqual(request.credits_cost, 5, "Credits should be 5 for 0.5 hours")

    def test_overlap_constraints(self):
        """Test prevention of double booking"""
        start_time = datetime.now().replace(microsecond=0)
        
        # Create first request: Start T, Duration 2h -> End T+2
        request1 = self.AccessRequest.create({
            'membership_id': self.membership.id,
            'service_id': self.service.id,
            'date_scheduled': start_time,
            'duration_hours': 2.0,
            'state': 'approved', # Assuming only approved/pending block? Check constraint logic.
        })
        # Constraint checks 'pending' or 'approved' usually? 
        # Logic implemented: state not in ['rejected', 'cancelled']
        # So 'draft' also blocks? Let's verify logic. 
        # Logic: if record.state in ['rejected', 'cancelled']: continue.
        # So 'draft', 'pending', 'approved' are checked.

        # Case 1: Overlap at start
        # Start T+1, Duration 2h -> Start inside Request1 (T to T+2)
        with self.assertRaises(ValidationError, msg="Should raise overlap error at start"):
            self.AccessRequest.create({
                'membership_id': self.membership.id,
                'service_id': self.service.id,
                'date_scheduled': start_time + timedelta(hours=1),
                'duration_hours': 2.0,
            })

        # Case 2: Complete overlap (inside)
        # Start T+0.5, Duration 1h -> Inside Request1
        with self.assertRaises(ValidationError, msg="Should raise overlap error inside"):
            self.AccessRequest.create({
                'membership_id': self.membership.id,
                'service_id': self.service.id,
                'date_scheduled': start_time + timedelta(hours=0.5),
                'duration_hours': 1.0,
            })

        # Case 3: Enveloping overlap
        # Start T-1, Duration 4h -> Envelops Request1
        with self.assertRaises(ValidationError, msg="Should raise overlap error enveloping"):
            self.AccessRequest.create({
                'membership_id': self.membership.id,
                'service_id': self.service.id,
                'date_scheduled': start_time - timedelta(hours=1),
                'duration_hours': 4.0,
            })

        # Case 4: No overlap (after)
        # Start T+2, Duration 1h -> Starts exactly when Request1 ends.
        # My logic: date_scheduled < end_date. T+2 < T+2 is False. So VALID.
        request2 = self.AccessRequest.create({
            'membership_id': self.membership.id,
            'service_id': self.service.id,
            'date_scheduled': start_time + timedelta(hours=2),
            'duration_hours': 1.0,
        })
        self.assertTrue(request2, "Should allow booking immediately after")
