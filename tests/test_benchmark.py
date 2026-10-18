import unittest
from tools.benchmark_dataset import metrics
class MetricsTests(unittest.TestCase):
 def row(self,y,p=None,status='done'):
  return dict(expected=y,verdict='violation' if p else 'no_violation',status=status,expected_types=['a'] if y else [],predicted_types=['a'] if p else [],elapsed_sec=10)
 def test_error_is_not_a_completed_negative(self):
  m=metrics([self.row(True,True),self.row(True,status='failed'),self.row(False,False)])
  self.assertEqual(m['recall_all'],.5);self.assertEqual(m['recall_completed'],1);self.assertEqual(m['positive_errors'],1);self.assertEqual(m['fn_completed'],0)
 def test_constant_alert_can_have_perfect_recall_without_specificity(self):
  m=metrics([self.row(True,True),self.row(False,True)])
  self.assertEqual(m['recall_all'],1);self.assertEqual(m['specificity_all'],0);self.assertEqual(m['precision'],.5);self.assertEqual(m['balanced_accuracy_all'],.5)
 def test_type_hit_is_distinct_from_binary_hit(self):
  r=self.row(True,True);r['predicted_types']=['b'];m=metrics([r]);self.assertEqual(m['tp'],1);self.assertEqual(m['primary_type_hits'],0)
