"""Fixed development criteria. No clip names, labels or annotation timestamps.
Formula AST is evaluated in code with Kleene three-valued logic.
"""
from copy import deepcopy

def allof(*ids):return {'all':list(ids)}
def anyof(*ids):return {'any':list(ids)}
def criterion(code,facts,formula=None,forbidden=None):
 return {'id':code,'facts':{f'P{i+1}':text for i,text in enumerate(facts)},'formula':formula or allof(*(f'P{i+1}' for i in range(len(facts)))),'must_not_require':forbidden or []}
CRITERIA=[
criterion('recount_after_partial_return_missing',[
 'Customer cash was received and counted, then a part of that same cash was returned to that customer.',
 'The remaining cash was accepted/stored or that transaction finished.',
 'The complete relevant interval is visible and the remaining cash was NOT recounted before acceptance/completion. A sampled missing gesture is unknown, not supported.'
]),
criterion('identity_check_missing',[
 'The beginning of a customer cash receipt operation is visible.',
 'Over the complete visible identification opportunity BEFORE receipt, neither a physical NOR digital identity verification occurs. A start outside the clip or unreadable identity procedure is unknown.'
],forbidden=['A physical document is not required when digital identification is visible.']),
criterion('previous_cash_unsecured',[
 'Two successive customer operations are supported, with the earlier customer cash provenance tracked.',
 'The earlier operation ends before the next operation starts.',
 'That earlier cash remains outside secured storage when the next customer operation starts.'
]),
criterion('workstation_unlocked_unattended',[
 'The cashier visibly leaves the workstation.',
 'AFTER departure, a readable working application or active unlocked work session is directly distinguishable on the screen. Lit display, open laptop lid or absence of a visible locking gesture are NOT proof. If screen contents are unreadable, this fact MUST be unknown.'
],forbidden=['Do not substitute a lit screen or absence of a locking gesture for visible accessible working session.']),
criterion('safe_accessible_to_clients',[
 'A visible object is identified as the cash safe, based on use/visible structure.',
 'The intended customer-accessible side is independently established from functional layout/service boundary, not seat or door-facing direction.',
 'The cash safe is physically reachable from that customer side without crossing a secured functional boundary.'
]),
criterion('cashier_area_access_unsecured',[
 'The cashier visibly leaves the cash area.',
 'After departure an entrance/barrier is directly seen to permit unsecured access; no locking gesture being observed is insufficient.',
 'Through that observed accessible entrance, visitors can physically reach the cash workspace/storage.'
]),
criterion('collection_bag_inspection_missing',[
 'A bank-valuable collection bag, not a personal bag, is visibly received.',
 'That received bag is then put into storage.',
 'Across the completely visible relevant handover-to-storage interval, the required packaging/lock/seal inspection is visibly skipped. Unobserved intervals make this unknown.'
]),
criterion('concurrent_customer_operations',[
 'Two separate customer money/document operations, not companions or internal work, are visibly established.',
 'The second operation begins while the first operation is visibly unfinished.'
]),
criterion('safe_left_open',[
 'The cashier visibly removes cash from the safe.',
 'The cashier finishes that safe access and returns to unrelated work or leaves.',
 'After that safe-access completion, the same safe door visibly remains open. Brief active access alone is not a violation.'
]),
criterion('safe_key_unattended',[
 'An identifiable key associated with the safe is directly visible, not just an unidentified small object or lock/hand gesture.',
 'The cashier places/leaves that safe key on an unsecured accessible surface.',
 'The cashier subsequently leaves and that same key visibly remains there without being retrieved or secured; retain the object continuity.'
],forbidden=['No customer, cash transaction, open safe door, or key inserted in a lock is required.']),
criterion('safe_key_left_in_lock',[
 'An identifiable key is directly visible inserted in the safe lock. A dark lock spot or hand gesture alone is unknown.',
 'Safe work ends and the cashier switches to other work OR leaves.',
 'After that transition the same key visibly remains inserted in the lock.'
],forbidden=['The cashier need not leave the room; switching to other work is sufficient. No visible customer or cash handover is required.']),
criterion('cash_left_unattended',[
 'The cashier visibly leaves the room/workplace, rather than just a client leaving.',
 'After that departure identifiable banknotes remain on the desk outside secured storage.'
]),
criterion('client_in_cashier_zone',[
 'The moving person is independently identified as a customer from their operational behavior, not appearance or seat.',
 'The intended cashier side is independently established from the functional service boundary/equipment layout.',
 'That customer crosses into that cashier side or behind the cashier with direct access to cash equipment.'
]),
criterion('zones_not_separated',[
 'An intended cashier/customer functional boundary and cash equipment/access path are independently established.',
 'The visible layout permits visitors direct passage behind the cashier to cash equipment/safe without a separating barrier.'
]),
criterion('cashier_works_client_side',[
 'The same operator is independently identified as cashier by responsibility for bank operations.',
 'The intended customer side/seat is independently established from service layout, not orientation or arbitrary chair.',
 'That cashier performs cash/equipment work from that customer side while the intended cashier workplace is unused.'
]),
criterion('count_without_customer',[
 'The counted/received cash is linked to a visible customer receipt operation, not internal inventory or own money.',
 'The cashier receives/counts that customer cash.',
 'At that same receipt/counting interval the corresponding customer has visibly left or is visibly absent.'
]),
criterion('clients_cash_not_separated',[
 'Two distinct customer cash transactions and the provenance of their separate funds are visibly established; two companions or one split pile do not suffice.',
 'The earlier customer cash remains on the work surface outside secured storage when the newer operation begins.',
 'New customer cash is placed beside that earlier cash before the earlier cash is secured; physical combining is NOT required.'
],forbidden=['Do not require physical mixing, simultaneous handover or absence of the earlier client. Adjacent cash from the two operations suffices.']),
criterion('clients_cash_mixed',[
 'Cash from two distinct supported customer transactions has separate established provenance.',
 'Those funds are visibly physically combined into one pile; adjacent distinct piles alone are insufficient.'
]),
criterion('personal_items',[
 'The owner/handler of the item is the cashier, supported by the same person continuing operational work. A single operator can be cashier without a customer; changing clothing/seat does not change role.',
 'An identifiable personal outerwear item of that cashier is placed OR rests on the cash working surface at some visible point. Evaluate the coat alone: absence/location/timing of a bag CANNOT negate this fact.',
 'An identifiable personal bag of that cashier is placed OR rests on the cash working surface at some visible point. Evaluate the bag alone: absence/location/timing of a coat CANNOT negate this fact.'
],formula=allof('P1',anyof('P2','P3')),forbidden=['No simultaneous coat AND bag placement. EITHER coat OR bag suffices.','No customer, cash transaction, counting money, prolonged stay or interruption of work is required.','The coat and bag need not be on the table at the same time; no shared timestamp across P2/P3.']),
criterion('cash_unsecured_during_personal_activity',[
 'The cashier has visibly finished counting identifiable banknotes.',
 'Those same banknotes remain unsecured on the desk.',
 'While those banknotes remain unsecured, the cashier switches to unrelated personal activity, such as drinking, rather than continued bank operation.'
])]

def evaluate(formula,statuses):
 if isinstance(formula,str):return statuses.get(formula,'unknown')
 op,children=next(iter(formula.items()));values=[evaluate(child,statuses) for child in children]
 if op=='all':return 'contradicted' if 'contradicted'in values else 'unknown' if 'unknown'in values else 'supported'
 if op=='any':return 'supported' if 'supported'in values else 'unknown' if 'unknown'in values else 'contradicted'
 raise ValueError('Unknown formula operator')
def proof_ids(formula,statuses):
 if isinstance(formula,str):return [formula] if statuses.get(formula)=='supported' else []
 op,children=next(iter(formula.items()))
 if op=='all':return sum((proof_ids(c,statuses) for c in children),[])
 for child in children:
  if evaluate(child,statuses)=='supported':return proof_ids(child,statuses)
 return []

def catalog(old):
 index={r['id']:r for r in old}
 return [{**deepcopy(index[c['id']]),**deepcopy(c)} for c in CRITERIA]
