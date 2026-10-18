const $=id=>document.getElementById(id);
let videoUrl=null, selection=0;
const eventNames={client_present:'Клиент у кассы',client_enters:'Вход клиента',client_leaves:'Выход клиента',document_handover:'Передача документа',cash_handover:'Передача наличных',cash_on_desk_unattended:'Наличные без присмотра',counting_machine_used:'Работа счетчика',safe_open:'Сейф открыт',safe_closed:'Сейф закрыт',cashier_leaves_room:'Выход кассира',cash_received_by_cashier:'Прием наличных',cash_paid_to_client:'Выдача наличных',manual_cash_count:'Ручной пересчет',cash_stored:'Помещение наличных на хранение',transaction_finished:'Завершение обслуживания',cash_to_personal_storage:'Наличные в личных вещах',personal_bag_in_cashier_zone:'Личная сумка в зоне кассира',previous_client_cash_on_desk:'Наличные предыдущего клиента на столе',unpacked_banknotes_paid:'Выдача неупакованных банкнот',collection_bag_received:'Прием инкассаторской сумки',bag_inspected:'Осмотр сумки',bag_visibly_damaged:'Видимое повреждение сумки',collector_leaves:'Выход инкассатора'};
const format=t=>`${Math.floor(t/60).toString().padStart(2,'0')}:${(t%60).toFixed(1).padStart(4,'0')}`;
$('file').addEventListener('change',()=>{
 selection++;
 const f=$('file').files[0];if(!f)return;
 $('filename').textContent=f.name;
 if(videoUrl)URL.revokeObjectURL(videoUrl);
 videoUrl=URL.createObjectURL(f);$('player').src=videoUrl;$('player').hidden=false;
});
function text(tag,value,cls){const el=document.createElement(tag);el.textContent=value;if(cls)el.className=cls;return el;}
function show(result){
 $('empty').hidden=true;$('verdict').hidden=false;
 $('verdict').textContent=result.verdict==='violation'?'Обнаружены признаки возможных нарушений':'Признаки по включенным правилам не обнаружены';
 $('verdict').className=result.verdict==='violation'?'warning':'';
 $('events').replaceChildren();
 for(const v of result.violations||[]){
  const card=document.createElement('article');card.className='event';
  const title=text('h3',v.type);const time=text('button',format(v.timecode_sec),'time');
  time.onclick=()=>{$('player').currentTime=v.timecode_sec;$('player').play().catch(()=>{});};
  card.append(time,title,text('p',v.description));
  const images=document.createElement('div');images.className='frames';
  for(const f of v.evidence_frames){const fig=document.createElement('figure');const img=document.createElement('img');
   img.src='data:image/jpeg;base64,'+f.image_base64;img.alt='Кадр-доказательство '+format(f.timestamp_sec);
   img.onclick=()=>{const dialog=document.createElement('dialog');dialog.style.maxWidth='95vw';const big=img.cloneNode();big.style.maxWidth='85vw';const close=text('button','Закрыть');close.onclick=()=>dialog.remove();dialog.append(big,close);document.body.append(dialog);dialog.showModal();};
   fig.append(img,text('figcaption',format(f.timestamp_sec)));images.append(fig);
  }card.append(images);
  if(v.rule){const link=text('a',`${v.rule.document} · ${v.rule.clause}`,'source');link.href=v.rule.url;link.target='_blank';link.rel='noopener noreferrer';card.append(link);}
  $('events').append(card);
 }
 $('limitations').textContent=(result.limitations||[]).join(' ');
 $('uncertain-rows').replaceChildren();
 const pending=result.review_candidates||[];
 $('uncertain').hidden=!pending.length;$('uncertain-title').textContent=`Не удалось подтвердить или исключить: ${pending.length} критериев`;
 for(const c of pending){const row=text('p',`${c.type} · ${format(c.timecode_sec)} · ${c.reason}`,'small');$('uncertain-rows').append(row);}
 $('timeline-rows').replaceChildren();
 $('timeline').hidden=!(result.event_timeline||[]).length;
 for(const w of result.event_timeline||[]){
  const row=document.createElement('article');row.className='event';
  const seek=text('button',format(w.start_sec),'time');
  seek.onclick=()=>{$('player').currentTime=w.start_sec;};
  const count=Object.values(w.facts||{}).filter(f=>f.state==='yes').length;
  row.append(seek,text('p',w.observed||'Недостаточно видимых данных'));
  const facts=document.createElement('ul');
  for(const [name,f] of Object.entries(w.facts||{})){
   if(f.state==='yes')facts.append(text('li',`${eventNames[name]||name} · ${format(f.time)} · оценка модели ${Math.round(f.confidence*100)}%`));
  }
  row.append(facts,text('small',w.operation?`Наблюдаемая операция: ${w.operation}`:`${count} наблюдаемых событий`));
  $('timeline-rows').append(row);
 }
}
$('analyze').onclick=async()=>{
 const file=$('file').files[0],key=$('key').value.trim();
 if(!file||(!key&&!galleryAuthenticated)){$('status').textContent='Выберите видео и введите ключ доступа.';return;}
 if(file.size>128*1024*1024){$('status').textContent='Размер файла превышает 128 МБ.';return;}
 selection++;
 $('analyze').disabled=true;$('progress').hidden=false;$('status').textContent='Загрузка записи…';
 $('events').replaceChildren();$('verdict').hidden=true;$('timeline').hidden=true;$('uncertain').hidden=true;$('limitations').textContent='';
 const start=Date.now(),headers={'X-API-Key':key};
 try{
  const data=new FormData();data.append('file',file);
  let response=await fetch('/api/v1/analyze',{method:'POST',headers,body:data});
  let body=await response.json();if(!response.ok)throw Error(body.detail||'Ошибка загрузки');
  const job=body.job_id;
  while(Date.now()-start<310000){
   await new Promise(r=>setTimeout(r,1500));
   response=await fetch(`/api/v1/jobs/${job}`,{headers});body=await response.json();
   if(!response.ok)throw Error(body.detail||'Не удалось получить результат');
   $('elapsed').textContent=Math.round((Date.now()-start)/1000)+' сек';
   $('status').textContent=body.stage||'Анализ записи…';
   if(body.status==='failed')throw Error(body.error||'Не удалось обработать видео');
   if(body.status==='done'){show(body);$('status').textContent='Проверка завершена';return;}
  }throw Error('Время ожидания истекло. Проверьте доступность сервиса.');
 }catch(e){$('status').textContent=e.message;}finally{$('analyze').disabled=false;$('progress').hidden=true;}
};

let exampleData=null, examplesLoading=false, galleryAuthenticated=false, sessionKey='';
const galleryPage=location.pathname==='/examples';
let galleryAccess=null;
if(galleryPage){
 document.body.classList.add('gallery-page');document.title='Видеопримеры — CashGuard';
 document.querySelector('main').prepend($('examples'));
 const heading=$('examples-count').parentElement,newHeading=text('h1','Видеопримеры ');
 newHeading.append($('examples-count'));heading.replaceWith(newHeading);
 galleryAccess=text('div','','gallery-access');galleryAccess.append(document.querySelector('label[for="key"]'),$('key'));
 $('examples').insertBefore(galleryAccess,$('examples-summary'));
}
const videoObserver=new IntersectionObserver(entries=>{
 for(const entry of entries)if(entry.isIntersecting){
  const player=entry.target;player.src=player.dataset.src;player.preload='metadata';videoObserver.unobserve(player);
 }
},{rootMargin:'250px'});
const states={queued:'В очереди',processing:'Обрабатывается',done:'Готово',failed:'Ошибка'};
function renderExamples(){
 if(!exampleData)return;
 const items=exampleData.items||[],done=items.filter(x=>x.status==='done'),failed=items.filter(x=>x.status==='failed');
 $('examples-count').textContent=`· ${items.length}`;
 const matches=done.filter(x=>x.matches_reference).length;
 const pending=items.length-done.length-failed.length;
 $('examples-summary').textContent=`${exampleData.model_label||"Qwen3.6 · финальная версия"} · обработано ${done.length} из ${items.length} · совпадений с разметкой ${matches} из ${done.length}`+(failed.length?` · ошибок ${failed.length}`:'')+(pending?` · осталось ${pending}`:' · прогон завершён');
 videoObserver.disconnect();$('examples-grid').replaceChildren();
 const filter=$('examples-filter').value;
 const shown=items.filter(x=>filter==='all'||(filter==='done'&&x.status==='done')||(filter==='failed'&&x.status==='failed')||(filter==='mismatch'&&x.status==='done'&&!x.matches_reference)||(filter==='type_mismatch'&&x.status==='done'&&x.expected_violation&&!(x.primary_type_matches||[]).length)||(filter==='violation'&&x.status==='done'&&x.verdict==='violation'));
 for(const item of shown){
  const card=text('article','','example-card');card.dataset.exampleId=item.id;
  const head=text('div','','example-head');head.append(text('h3',item.filename),text('span',states[item.status]||item.status,'example-state '+item.status));card.append(head);
  if(item.video_ready){
   const player=document.createElement('video');player.className='example-video';player.controls=true;player.muted=true;player.playsInline=true;player.preload='none';
   player.setAttribute('aria-label','Видеопример '+item.filename);player.dataset.src=`/api/v1/examples/${item.id}/video`;
   card.append(player);videoObserver.observe(player);
   const direct=text('a','Открыть видео отдельно ↗','direct-video');direct.href=player.dataset.src;direct.target='_blank';direct.rel='noopener';card.append(direct);
  }
  card.append(text('p','Разметка: '+(item.expected_violation?'есть нарушение':'без нарушения')+(item.expected_timestamp_sec!=null?` · ${format(item.expected_timestamp_sec)}`:''),'reference'));
  if(item.human_type)card.append(text('p','Тип по разметке: '+item.human_type,'reference'));
  if(item.status==='done'){
   card.append(text('p','Qwen3.6: '+(item.verdict==='violation'?`найдены признаки (${item.violation_count})`:'признаки не обнаружены'),'model-answer'));
   card.append(text('p',item.matches_reference?'Бинарная метка совпала':'Бинарная метка не совпала',item.matches_reference?'comparison match':'comparison mismatch'));
   if(item.expected_violation&&(item.expected_types||[]).length)card.append(text('p',(item.primary_type_matches||[]).length?'Основной тип из разметки найден':'Основной тип из разметки не найден','comparison'));
   card.append(text('p',`Обработка: ${Math.round(item.elapsed_sec)} сек`,'small'));
   const open=text('button','Открыть результат проверки ↗');open.onclick=()=>openExample(item);card.append(open);
  }else if(item.status==='failed'){card.append(text('p',item.error||'Не удалось обработать видео','small'));}
  else{card.append(text('p',item.status==='processing'?'Видео проходит анализ на сервере.':'Результат появится после обработки.','small'));}
  $('examples-grid').append(card);
 }
 if(!shown.length)$('examples-grid').append(text('p','Нет видео с выбранным фильтром.','small'));
}
async function loadExamples(){
 const key=$('key').value.trim();if(examplesLoading)return;
 examplesLoading=true;
 try{
  const headers=key?{'X-API-Key':key}:{};
  if(key&&sessionKey!==key){
   const login=await fetch('/api/v1/session',{method:'POST',headers});
   if(!login.ok)throw Error('Проверьте ключ доступа.');
   sessionKey=key;
  }
  const response=await fetch('/api/v1/examples',{headers,cache:'no-store'});
  if(!response.ok)throw Error(response.status===401?'Введите ключ доступа выше, чтобы открыть примеры.':'Не удалось загрузить примеры.');
  galleryAuthenticated=true;
  if(galleryAccess)galleryAccess.hidden=true;
  if(!key)$('key').placeholder='Сессия активна';
  exampleData=await response.json();renderExamples();
 }catch(e){$('examples-summary').textContent=e.message;}finally{examplesLoading=false;}
}
async function openExample(item){
 const token=++selection,headers={'X-API-Key':$('key').value.trim()};
 $('examples-selected').textContent=`Открываем ${item.filename}…`;
 try{
  const response=await fetch(`/api/v1/examples/${item.id}`,{headers});
  if(!response.ok)throw Error('Не удалось открыть результат.');
  const body=await response.json();if(token!==selection)return;
  $('file').value='';$('filename').textContent='Выберите видеозапись';
  $('player').pause();$('player').removeAttribute('src');$('player').hidden=true;
  show(body.result);$('elapsed').textContent=`${item.filename} · ${Math.round(item.elapsed_sec)} сек`;
  $('status').textContent=`Сохранённый пример: ${item.filename}. Разметка: ${item.expected_violation?'есть нарушение':'без нарушения'}.`;
  $('examples-selected').textContent=`Результат ${item.filename} открыт выше. Загрузка видео…`;
  document.querySelector('.review').scrollIntoView({behavior:'smooth',block:'start'});
  if(item.video_ready){
   const media=await fetch(`/api/v1/examples/${item.id}/video`,{headers});
   if(!media.ok)throw Error('Результат открыт, но видео недоступно.');
   const blob=await media.blob();if(token!==selection)return;
   if(videoUrl)URL.revokeObjectURL(videoUrl);
   videoUrl=URL.createObjectURL(blob);$('player').src=videoUrl;$('player').hidden=false;
   $('examples-selected').textContent=`Открыт пример ${item.filename}. Видео и сохранённый результат показаны выше.`;
  }else{$('examples-selected').textContent=`Открыт результат ${item.filename}. Видеопревью ещё готовится.`;}
 }catch(e){if(token===selection)$('examples-selected').textContent=e.message;}
}
$('examples-refresh').onclick=loadExamples;
$('examples-filter').onchange=renderExamples;
$('key').addEventListener('change',loadExamples);
let keyTimer;
$('key').addEventListener('input',()=>{clearTimeout(keyTimer);keyTimer=setTimeout(loadExamples,500);});
setInterval(()=>{if(document.visibilityState==='visible'&&(!exampleData||exampleData.status==='processing')&&(galleryAuthenticated||$('key').value.trim()))loadExamples();},10000);
loadExamples();
