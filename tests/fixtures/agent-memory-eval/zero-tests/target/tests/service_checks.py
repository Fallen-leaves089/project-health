from __future__ import annotations

import unittest


class ServiceChecks(unittest.TestCase):
    def test_invoice_rounding(self) -> None:
        self.assertEqual(round(2.675, 2), 2.68)
