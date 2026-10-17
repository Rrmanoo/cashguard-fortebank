"""Deterministic procedure state machines; uncertainty never becomes an omission."""
from dataclasses import dataclass, field

@dataclass
class Procedure:
    receipt: dict | None = None
    client_left: bool = False
    closed: bool = False
    bag: dict | None = None
    findings: list = field(default_factory=list)

    def step(self,w):
        facts=w['facts']
        def yes(name):
            f=facts.get(name)
            return f if f and f['state']=='yes' and f['confidence']>=.75 else None
        def no(name):
            f=facts.get(name)
            return f if f and f['state']=='no' and f['confidence']>=.85 else None
        def emit(rule,f,context=None):
            if any(x['rule_id']==rule and abs(x['time']-f['time'])<6 for x in self.findings):return
            self.findings.append({'rule_id':rule,'time':f['time'],
              'confidence':min(f['confidence'],(context or f)['confidence']),
              'evidence_times':list(dict.fromkeys([(context or f)['time'],f['time']])),
              'observed':w['annotation'].observed})
        if yes('client_enters'):
            self.receipt=None; self.client_left=False; self.closed=False
        if f:=yes('cash_received_by_cashier'):
            self.receipt=f; self.client_left=False; self.closed=False
        if yes('transaction_finished'): self.closed=True
        if yes('client_leaves') and w['annotation'].doorway_visible=='yes':self.client_left=True
        if self.receipt and not self.closed:
            if (f:=yes('cashier_leaves_room')) and yes('client_present') and w['annotation'].doorway_visible=='yes':
                emit('cashier_leaves',f,self.receipt)
            if self.client_left and no('client_present'):
                f=yes('manual_cash_count') or yes('counting_machine_used')
                if f:emit('count_without_customer',f,self.receipt)
        if f:=yes('cash_to_personal_storage'):emit('cash_to_personal_storage',f)
        if f:=yes('personal_bag_in_cashier_zone'):emit('personal_items',f)
        # Explicit cross-client continuity is required; unattended cash alone is insufficient.
        if (f:=yes('previous_client_cash_on_desk')) and yes('client_present'):
            emit('previous_cash_unsecured',f)
        # Omission-based rules are deliberately not enabled at 2.5fps: sampled non-detection
        # cannot prove absence of a quick manual count, seal inspection or electronic action.
        if yes('client_enters') or (self.receipt and w['end']-self.receipt['time']>120):
            if not yes('cash_received_by_cashier'):self.receipt=None

def evaluate(windows):
    machine=Procedure()
    for w in windows:machine.step(w)
    return sorted(machine.findings,key=lambda f:f['time'])
