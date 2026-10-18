# Каталог 20 типов

Фиксированные предикаты и формулы находятся в `rules/criteria.json`; ниже — обзор. Это визуальные гипотезы для проверки, а не автоматическое юридическое заключение.

| ID | Тип | Формула | Основание |
|---|---|---|---|
| `recount_after_partial_return_missing` | Нет контрольного пересчёта остатка | `{'all': ['P1', 'P2', 'P3']}` | пп. 19(2), 20 (operational_interpretation) |
| `identity_check_missing` | Нет предварительной идентификации | `{'all': ['P1', 'P2']}` | п. 19(1) (direct_with_applicability) |
| `previous_cash_unsecured` | Деньги предыдущего клиента не убраны | `{'all': ['P1', 'P2', 'P3']}` | п. 20 (direct_with_applicability) |
| `workstation_unlocked_unattended` | Компьютер оставлен без блокировки | `{'all': ['P1', 'P2']}` | Требования информационной безопасности, контекст рабочего места (operational_interpretation) |
| `safe_accessible_to_clients` | Сейф находится в клиентской зоне | `{'all': ['P1', 'P2', 'P3']}` | п. 5; требования к устройству кассового узла (operational_interpretation) |
| `cashier_area_access_unsecured` | Кассовая зона оставлена доступной | `{'all': ['P1', 'P2', 'P3']}` | пп. 14, 80; применимость к входу требует проверки (operational_interpretation) |
| `collection_bag_inspection_missing` | Сумка принята без осмотра | `{'all': ['P1', 'P2', 'P3']}` | п. 24(3–4) (direct_with_applicability) |
| `concurrent_customer_operations` | Перекрытие операций клиентов | `{'all': ['P1', 'P2']}` | пп. 20–22 (operational_interpretation) |
| `safe_left_open` | Сейф оставлен открытым | `{'all': ['P1', 'P2', 'P3']}` | пп. 20, 80 (operational_interpretation) |
| `safe_key_unattended` | Ключ от сейфа оставлен без присмотра | `{'all': ['P1', 'P2', 'P3']}` | п. 80 (operational_interpretation) |
| `safe_key_left_in_lock` | Ключ оставлен в замке сейфа | `{'all': ['P1', 'P2', 'P3']}` | п. 80 (operational_interpretation) |
| `cash_left_unattended` | Наличные оставлены без присмотра | `{'all': ['P1', 'P2']}` | пп. 14, 20, 80 (operational_interpretation) |
| `client_in_cashier_zone` | Клиент вошёл в рабочую зону | `{'all': ['P1', 'P2', 'P3']}` | пп. 5, 14; требования к доступу (operational_interpretation) |
| `zones_not_separated` | Не разделены кассовая и клиентская зоны | `{'all': ['P1', 'P2']}` | п. 5; требования к устройству кассового узла (operational_interpretation) |
| `cashier_works_client_side` | Кассир работает со стороны клиента | `{'all': ['P1', 'P2', 'P3']}` | пп. 5, 14; функциональная организация кассы (operational_interpretation) |
| `count_without_customer` | Пересчёт денег клиента без клиента | `{'all': ['P1', 'P2', 'P3']}` | п. 20 (direct_with_applicability) |
| `clients_cash_not_separated` | Наличные разных клиентов не разделены | `{'all': ['P1', 'P2', 'P3']}` | п. 20 (direct_with_applicability) |
| `clients_cash_mixed` | Смешаны деньги разных клиентов | `{'all': ['P1', 'P2']}` | п. 20 (direct_with_applicability) |
| `personal_items` | Личные вещи на рабочей поверхности | `{'all': ['P1', {'any': ['P2', 'P3']}]}` | п. 12 (direct_with_applicability) |
| `cash_unsecured_during_personal_activity` | Деньги оставлены при личных действиях | `{'all': ['P1', 'P2', 'P3']}` | пп. 14, 20; операционная интерпретация (operational_interpretation) |
