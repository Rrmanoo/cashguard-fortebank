import http from 'node:http';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';

const keyPath = fileURLToPath(new URL('./access.key', import.meta.url));
const apiKey = fs.readFileSync(keyPath, 'utf8').trim();
if (apiKey.length < 24) throw new Error('The local viewer needs the existing server key');
const origins = new Set(['http://127.0.0.1:9017', 'http://localhost:9017']);
const hosts = new Set(['127.0.0.1:9017', 'localhost:9017']);
const manifest = await new Promise((resolve, reject) => {
  http.get({host:'127.0.0.1',port:9019,path:'/api/v1/examples',headers:{'X-API-Key':apiKey}}, remote => {
    const chunks=[];remote.on('data',chunk=>chunks.push(chunk));
    remote.on('end',()=>{
      try {if(remote.statusCode!==200)throw Error('Examples unavailable');resolve(JSON.parse(Buffer.concat(chunks).toString()));}
      catch(error){reject(error);}
    });
  }).on('error',reject);
});
const escape = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function renderHtml(html, path) {
  const items=manifest.items||[],done=items.filter(item=>item.status==='done');
  const summary=`Обработано ${done.length} из ${items.length} · совпадений с разметкой ${done.filter(item=>item.matches_reference).length} из ${done.length} · прогон завершён`;
  const cards=items.map(item=>{
    if(!/^[a-f0-9]{16}$/.test(item.id))return '';
    const video=`/api/v1/examples/${item.id}/video`;
    return `<article class="example-card"><div class="example-head"><h3>${escape(item.filename)}</h3><span class="example-state done">Готово</span></div><video class="example-video" controls muted playsinline preload="none" src="${video}" aria-label="Видеопример ${escape(item.filename)}"></video><p class="reference">Разметка: ${item.expected_violation?'есть нарушение':'без нарушения'}</p><p class="model-answer">Модель: ${item.verdict==='violation'?'найдены признаки':'признаки не обнаружены'}</p><p class="comparison ${item.matches_reference?'match':'mismatch'}">${item.matches_reference?'Совпадает с разметкой':'Расхождение с разметкой'}</p><p><a href="${video}" target="_blank" rel="noopener">Открыть видео отдельно ↗</a></p></article>`;
  }).join('');
  html=html.replace('<div id="examples-grid" class="examples-grid"></div>',`<div id="examples-grid" class="examples-grid">${cards}</div>`)
    .replace(/(<div id="examples-summary"[^>]*>)[^<]*(<\/div>)/,`$1${escape(summary)}$2`)
    .replace('<span id="examples-count" class="small"></span>',`<span id="examples-count" class="small">· ${items.length}</span>`);
  if(path.split('?')[0]==='/examples'){
    const section=html.match(/<section class="panel examples" id="examples">[\s\S]*?<\/section>/)?.[0];
    if(section)html=html.replace(section,'').replace('<main>','<main>'+section);
    html=html.replace('<body>','<body class="gallery-page">')
      .replace('<title>CashGuard — проверка кассовых операций</title>','<title>Видеопримеры — CashGuard</title>');
  }
  return html;
}
const server = http.createServer((request, response) => {
  const path = request.url || '/';
  if (!hosts.has(request.headers.host) || !/^\/(?!\/)/.test(path)) {
    response.writeHead(400); response.end('Invalid local request'); return;
  }
  if ((request.headers.origin && !origins.has(request.headers.origin)) ||
      (path.startsWith('/api/') && request.headers['sec-fetch-site'] === 'cross-site')) {
    response.writeHead(403); response.end('This viewer is only available from its local page'); return;
  }
  const headers = { ...request.headers, host: '127.0.0.1:9017' };
  delete headers.connection;
  delete headers['proxy-connection'];
  const media = /^\/api\/v1\/examples\/[a-f0-9]{16}\/video(?:\?|$)/.test(path);
  if (!media) {
    delete headers['if-none-match'];
    delete headers['if-modified-since'];
  }
  if (path.startsWith('/api/v1/')) headers['x-api-key'] = apiKey;
  const upstream = http.request({ host: '127.0.0.1', port: 9019, path,
    method: request.method, headers }, remote => {
    const outgoing = { ...remote.headers, 'x-frame-options': 'DENY',
      'content-security-policy': "frame-ancestors 'none'" };
    delete outgoing.connection;
    if (!media) {
      outgoing['cache-control'] = 'no-store, max-age=0';
      delete outgoing.etag;
      delete outgoing['last-modified'];
      delete outgoing.expires;
    }
    if(remote.statusCode===200 && String(remote.headers['content-type']).includes('text/html')){
      const chunks=[];remote.on('data',chunk=>chunks.push(chunk));
      remote.on('end',()=>{
        const body=Buffer.from(renderHtml(Buffer.concat(chunks).toString('utf8'),path));
        outgoing['content-length']=String(body.length);delete outgoing['transfer-encoding'];
        response.writeHead(200,outgoing);response.end(body);
      });
    }else{
      response.writeHead(remote.statusCode || 502, outgoing);
      remote.pipe(response);
    }
  });
  upstream.on('error', () => {
    if (!response.headersSent) response.writeHead(502, { 'content-type': 'text/plain; charset=utf-8' });
    response.end('Соединение с сервером недоступно. Требуется восстановить Teleport-туннель.');
  });
  response.on('close', () => upstream.destroy());
  request.pipe(upstream);
});
server.requestTimeout = 330000;
server.headersTimeout = 60000;
server.listen(9017, '127.0.0.1', () => {
  fs.unlinkSync(keyPath);
  console.log('CashGuard authenticated local viewer: http://127.0.0.1:9017/examples');
});
