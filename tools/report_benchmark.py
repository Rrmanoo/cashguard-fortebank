"""Publish aggregate metrics only; keep per-video evidence/report under private outputs."""
import argparse,collections,html,json,statistics
from pathlib import Path

def write(p,x):p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2))
def pct(x):return '—' if x is None else f'{x*100:.2f}%'
def report(benchmark,repo):
 root=Path(benchmark);repo=Path(repo);s=json.loads((root/'summary.json').read_text());rows=s['records'];catalog=json.loads((repo/'rules/criteria.json').read_text());k42=s['metrics_42'];k40=s['metrics_40_unique'];per=[]
 for c in catalog:
  typ=c['id'];truth=[r for r in rows if typ in r['expected_types']];pred=[r for r in rows if typ in r['predicted_types']];hit=sum(typ in r['predicted_types'] and r['status']=='done' for r in truth)
  per.append({'type_id':typ,'name':c['name'],'primary_reference_support':len(truth),'primary_matches':hit,'primary_recall':hit/len(truth) if truth else None,'predicted_on_all_videos':len(pred),'false_alerts_on_negative_videos':sum(not r['expected'] for r in pred)})
 completions=[json.loads(p.read_text()) for p in root.glob('traces/*/calls/**/completion.json')];attempts=len(list(root.glob('traces/*/calls/**/response-*.json')));thinking=sum(bool(c.get('reasoning_returned')) for c in completions)
 raw={k:v for k,v in s.items() if k not in ['records','duplicates']};raw['duplicate_pair_count']=len(s['duplicates']);raw['per_type_42']=per;raw['call_audit']={'completed_calls':len(completions),'http_attempts':attempts,'reasoning_returned_calls':thinking,'prompt_tokens':sum(c.get('usage',{}).get('prompt_tokens',0) for c in completions),'completion_tokens':sum(c.get('usage',{}).get('completion_tokens',0) for c in completions)};raw['always_alert_42']={'tp':22,'tn':0,'fp':20,'fn':0,'recall':1,'precision':22/42,'accuracy':22/42,'f1':44/64,'balanced_accuracy':.5};raw['historical_qwen36_five_rule_pipeline_42']={'tp':4,'tn':20,'fp':0,'fn':18,'recall':4/22,'precision':1,'accuracy':24/42,'f1':8/26,'timing_component_sum_seconds':1531.981,'timing_note':'Historical sum of preprocessing/model components; not paired wall time. Different rule set and architecture.'};raw['evaluation_scope']='Development set used to design criteria/prompts; no independent test. Extra types on positives are unverified. Errors count in recall_all denominator; hash duplicates expanded only for 42-file metric.'
 write(repo/'benchmarks/final/metrics.json',raw);protocol=json.loads((root/'protocol.json').read_text());write(repo/'benchmarks/final/protocol.json',protocol)
 vals=[('Recall (все положительные)',k42['recall_all'],k40['recall_all']),('Precision',k42['precision'],k40['precision']),('F1 (с ошибками в знаменателе)',k42['f1_all'],k40['f1_all']),('Accuracy',k42['accuracy_all'],k40['accuracy_all']),('Specificity',k42['specificity_all'],k40['specificity_all']),('Balanced accuracy',k42['balanced_accuracy_all'],k40['balanced_accuracy_all']),('Recall записанного основного типа',k42['primary_type_recall_all'],k40['primary_type_recall_all'])]
 md=f'''# Полный прогон · {s['version']}

Это development benchmark, а не независимый тест. Все уникальные ролики обработаны заново одной зафиксированной архитектурой; метки, их таймстемпы и имена файлов в модель не передавались. Приоритет — обнаружение, но Recall оценивается вместе с ложными тревогами и правильностью типа.

| Метрика | 42 файла | 40 уникальных |
|---|---:|---:|
'''+''.join(f'| {name} | {pct(a)} | {pct(b)} |\n' for name,a,b in vals)+f'''
42 файла: **TP {k42['tp']}, TN {k42['tn']}, FP {k42['fp']}, FN среди завершённых {k42['fn_completed']}**, ошибок на положительных {k42['positive_errors']}, всех ошибок {k42['failed']}. Завершено {k42['completed']}/42. Основных типов совпало **{k42['primary_type_hits']}/{k42['primary_reference_tags']}**. Выдано {k42['predicted_type_tags']} тегов, из них {k42['false_type_tags_on_negative_videos']} на отрицательных видео. Остальные дополнительные теги на положительных видео не имеют исчерпывающей разметки: корректный multiclass precision/F1 по ним неизвестен.

40 уникальных: TP {k40['tp']}, TN {k40['tn']}, FP {k40['fp']}, FN завершённых {k40['fn_completed']}, ошибок {k40['failed']}. Основные типы {k40['primary_type_hits']}/{k40['primary_reference_tags']}. В одной положительной дублированной паре один и тот же видеоряд размечен разными основными типами; уникальный подсчёт использует первую запись и не превращает вторую в независимое наблюдение. На одном ролике два основных типа, поэтому знаменатель типов отличается от числа положительных видео.

## Время

* Длительность всех 42 видео: **{s['video_seconds_file_weighted']:.3f} с / {s['video_seconds_file_weighted']/60:.3f} мин**.
* Длительность 40 уникальных: {s['video_seconds_unique']:.3f} с / {s['video_seconds_unique']/60:.3f} мин.
* Реальное время полного прогона: **{s['wall_seconds']:.3f} с / {s['wall_seconds']/60:.3f} мин**.
* Сумма времени 40 заданий: {s['sum_unique_job_seconds']:.3f} с / {s['sum_unique_job_seconds']/60:.3f} мин (перекрывающиеся интервалы, не wall time).
* На уникальное видео: median {s['unique_job_seconds']['median']:.3f} с, p95 {s['unique_job_seconds']['p95']:.3f} с, max {s['unique_job_seconds']['max']:.3f} с.
* Завершённых менее 300 с: {k42['completed_under_300_sec']}/42 файлов. Benchmark не включает загрузку файла жюри через Интернет; отдельный API smoke указан в validation.json, если выполнен.

Два видео одновременно, общая очередь до четырёх запросов Qwen. Время включает декодирование, все свежие запросы, выбор кропов и сборку доказательств; не включает подготовку отчёта. GPU нагрузка других процессов не контролировалась. Всего завершённых вызовов {len(completions)}, HTTP попыток {attempts}; непустой возвращённый reasoning — {thinking}. Thinking отключён; клиент не измеряет скрытые вычисления модели.

## Контроль сравнения

Константа «всегда нарушение»: Recall 100%, Precision/Accuracy 52,38%, F1 68,75%, Balanced accuracy 50%. Даже Recall 100% не является преимуществом, если система даёт ту же постоянную классификацию. Исторический Qwen3.6 с 5 правилами: TP4/TN20/FP0/FN18, Recall18,18%, Precision100%, F1 30,77%, Accuracy57,14%. Его время — сумма компонентов 1531,981 с; это иной протокол и не прямое сравнение скорости. Новая версия оценивает 20 типов и использует другой порядок визуальной проверки, поэтому причинный эффект отдельных изменений не изолирован.

## Основные типы (42 файла)

| Тип | Размечено | Найдено | Recall основного типа | Выдано всего | Ложные на отрицательных |
|---|---:|---:|---:|---:|---:|
'''+''.join(f"| {p['name']} | {p['primary_reference_support']} | {p['primary_matches']} | {pct(p['primary_recall'])} | {p['predicted_on_all_videos']} | {p['false_alerts_on_negative_videos']} |\n" for p in per)
 if k42['fp']>=15:md+='\n**Существенное ограничение:** высокая частота ложных тревог. Этот запуск не доказывает пригодность автоматического вердикта; пространственные и отсутствующие действия требуют дополнительной проверки и независимой валидации. Финальная версия сохранена как воспроизводимый прототип, а не сертифицированный контроль нарушений.\n'
 md+='\nПолные ответы, кадры, журнал, схемы и источники ошибок сохраняются приватно у команды. В публичном Git — только код и агрегаты.\n';(repo/'docs/submission/evaluation.md').write_text(md)
 # Private per-video report. Never copied into the public repository.
 cards=''
 for r in rows:
  pred=', '.join(r['predicted_types']) or '—';expected=', '.join(r['expected_types']) or 'без нарушения';cards+=f"<tr><td>{html.escape(r['filename'])}</td><td>{html.escape(expected)}</td><td>{html.escape(pred)}</td><td>{r['status']}</td><td>{r['elapsed_sec']:.2f} с</td></tr>"
 page='<html lang="ru"><meta charset="utf-8"><title>CashGuard · полный прогон</title><style>body{font:15px/1.5 system-ui;max-width:1400px;margin:auto;padding:24px}pre{white-space:pre-wrap}table{border-collapse:collapse;width:100%}td,th{padding:10px;border:1px solid #ddd;vertical-align:top}</style><h1>CashGuard: финальный прогон</h1><pre>'+html.escape(md)+'</pre><h2>Приватные результаты по видео</h2><table><tr><th>Файл</th><th>Основной тип разметки</th><th>Модель</th><th>Статус</th><th>Время</th></tr>'+cards+'</table><p><a href="summary.json">Все метрики и пути к полным ответам</a></p></html>'
 (root/'report.html').write_text(page)
 # Insert actual metrics into the primary README once.
 readme=repo/'README.md';t=readme.read_text();t=t.replace('Полный прогон финальной версии публикуется в `benchmarks/final/metrics.json` и [отчёте](docs/submission/evaluation.md). До завершения прогона численные результаты не заявляются.',f"Полный прогон завершён: **Recall {pct(k42['recall_all'])}, Precision {pct(k42['precision'])}, F1 {pct(k42['f1_all'])}, Accuracy {pct(k42['accuracy_all'])}**. TP{k42['tp']} / TN{k42['tn']} / FP{k42['fp']} / FN{k42['fn_completed']} (завершённые), ошибок {k42['failed']}. Основных типов найдено {k42['primary_type_hits']}/{k42['primary_reference_tags']}. Полное время {s['wall_seconds']/60:.2f} мин на {s['video_seconds_file_weighted']/60:.2f} мин видео. [Подробный анализ](docs/submission/evaluation.md), [агрегаты JSON](benchmarks/final/metrics.json).")
 readme.write_text(t);print(json.dumps({k:v for k,v in raw.items() if k in ['metrics_42','wall_seconds','metrics_40_unique','call_audit']},ensure_ascii=False,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--benchmark',required=True);p.add_argument('--repo',default=str(Path(__file__).resolve().parents[1]));a=p.parse_args();report(a.benchmark,a.repo)
