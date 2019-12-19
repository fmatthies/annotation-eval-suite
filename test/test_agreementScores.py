import os

from unittest import TestCase
from compare import comparison


class TestAgreementScores(TestCase):
    comp = comparison.BatchComparison(
        os.path.join("..", "test-resources", "index"),
        ["anno01", "anno02", "anno03", "anno04"],
        os.path.join("..", "test-resources")
    )

    def test_return_errors(self):
        self.fail()

    def test_get_dataframe(self):
        self.comp.get_comparison_obj("01").return_agreement_scores("Medication")
