import unittest
from types import SimpleNamespace
from app.release.logic import evaluate,proof_ids
from app.release.engine import factual_guards,CUSTOMER_TYPES
class ReleaseLogicTests(unittest.TestCase):
 def test_coat_does_not_require_bag(self):
  expr={'all':['P1',{'any':['P2','P3']}]};s={'P1':'supported','P2':'supported','P3':'unknown'}
  self.assertEqual(evaluate(expr,s),'supported');self.assertEqual(proof_ids(expr,s),['P1','P2'])
 def test_internal_cash_does_not_prove_customer_identity_failure(self):
  facts={'P1':{'status':'supported'},'P2':{'status':'supported'}}
  normalized,reasons=factual_guards('identity_check_missing',facts,SimpleNamespace(functional_boundary='unknown'),[{'customer_transaction':'contradicted'}],{})
  self.assertEqual(normalized['P1']['status'],'unknown');self.assertEqual(facts['P1']['status'],'supported');self.assertTrue(reasons)
 def test_unknown_boundary_cannot_be_promoted_to_intrusion(self):
  f={p:{'status':'supported'} for p in ['P1','P2','P3']};actual,_=factual_guards('client_in_cashier_zone',f,SimpleNamespace(functional_boundary='unknown'),[],{})
  self.assertEqual(evaluate({'all':['P1','P2','P3']},{p:v['status'] for p,v in actual.items()}),'unknown')
 def test_after_state_cannot_precede_departure(self):
  f={'P1':{'status':'supported','witness_image_id':'E01'},'P2':{'status':'supported','witness_image_id':'E00'}};actual,_=factual_guards('cash_left_unattended',f,SimpleNamespace(functional_boundary='unknown'),[],{'E00':{'timestamp_sec':0},'E01':{'timestamp_sec':5}})
  self.assertEqual(actual['P2']['status'],'unknown')
 def test_personal_items_do_not_need_a_customer(self):self.assertNotIn('personal_items',CUSTOMER_TYPES)
 def test_keys_do_not_need_a_customer(self):self.assertNotIn('safe_key_unattended',CUSTOMER_TYPES)
