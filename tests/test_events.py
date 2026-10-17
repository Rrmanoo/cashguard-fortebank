import unittest
from app.events import Window,Fact,normalize
from app.rules import evaluate

def window(t,yes=(),no=(),door='yes'):
    a=Window(facts=[Fact(event=n,state=s,confidence=.95,timestamp_sec=t) for s,names in [('yes',yes),('no',no)] for n in names],desk_visible='yes',doorway_visible=door,observed='Тест')
    return {'start':t,'end':t+2,'timestamps':[t,t+1,t+2],'annotation':a}
class RulesTests(unittest.TestCase):
    def run_rules(self,*windows):return evaluate(normalize(windows))
    def test_receipt_then_cashier_exit(self):
        result=self.run_rules(window(0,['cash_received_by_cashier']),window(3,['client_present','cashier_leaves_room']))
        self.assertEqual(result[0]['rule_id'],'cashier_leaves')
        self.assertEqual(result[0]['evidence_times'],[0,3])
    def test_finished_transaction_permits_exit(self):
        self.assertEqual(self.run_rules(window(0,['cash_received_by_cashier']),window(3,['transaction_finished']),window(6,['client_present','cashier_leaves_room'])),[])
    def test_payout_does_not_start_receipt_rule(self):
        self.assertEqual(self.run_rules(window(0,['cash_paid_to_client']),window(3,['client_present','cashier_leaves_room'])),[])
    def test_hidden_door_does_not_prove_exit(self):
        self.assertEqual(self.run_rules(window(0,['cash_received_by_cashier']),window(3,['client_present','cashier_leaves_room'],door='unknown')),[])
    def test_missing_client_does_not_prove_absence(self):
        self.assertEqual(self.run_rules(window(0,['cash_received_by_cashier']),window(3,['counting_machine_used'])),[])
    def test_count_after_visible_client_departure(self):
        r=self.run_rules(window(0,['cash_received_by_cashier']),window(3,['client_leaves']),window(6,['manual_cash_count'],['client_present']))
        self.assertEqual(r[0]['rule_id'],'count_without_customer')
    def test_no_machine_does_not_mean_no_count(self):
        self.assertEqual(self.run_rules(window(0,['cash_received_by_cashier'],['counting_machine_used']),window(3,['transaction_finished'])),[])
    def test_open_safe_and_unattended_cash_are_not_rules(self):
        self.assertEqual(self.run_rules(window(0,['safe_open','cash_on_desk_unattended'])),[])
    def test_fabricated_time_rejected(self):
        w=window(0,['cash_to_personal_storage']);w['annotation'].facts[0].timestamp_sec=999
        self.assertEqual(self.run_rules(w),[])
    def test_low_confidence_not_actionable(self):
        w=window(0,['cash_to_personal_storage']);w['annotation'].facts[0].confidence=.5
        self.assertEqual(self.run_rules(w),[])
    def test_new_client_resets_context(self):
        self.assertEqual(self.run_rules(window(0,['cash_received_by_cashier']),window(3,['client_enters']),window(6,['client_present','cashier_leaves_room'])),[])
    def test_transient_event_not_smoothed_away(self):
        self.assertEqual(len(self.run_rules(window(0),window(3,['cash_to_personal_storage']),window(6))),1)
