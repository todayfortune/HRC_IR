let report = null;
let editing = false;
const commentOrder = [
  ['미국증시','미국증시'],['국내증시','국내증시'],['방산','방산주'],['현대로템','현대로템'],['반도체','반도체']
];

const valueOrNull = value => value === undefined || value === null || value === '' ? null : Number(value);
const comma = (value, digits=0) => valueOrNull(value) === null ? '-' : Number(value).toLocaleString('ko-KR',{minimumFractionDigits:digits,maximumFractionDigits:digits});
const signClass = value => valueOrNull(value) === null ? 'empty' : Number(value)>0 ? 'up' : Number(value)<0 ? 'down' : 'zero';
const signed = (value, digits=0) => valueOrNull(value) === null ? '-' : `${Number(value)>0?'+':''}${comma(value,digits)}`;
const rate = value => valueOrNull(value) === null ? '-' : `${Number(value)>0?'▲':Number(value)<0?'▼':'－'}${Math.abs(Number(value)).toFixed(2)}%`;
const price = (value, kind='stock') => valueOrNull(value) === null ? '-' : kind==='index' ? comma(value,2) : kind==='fx' ? comma(value,2) : `${comma(value)}원`;
const marketCap = value => valueOrNull(value) === null ? '-' : `${(Number(value)/10000).toLocaleString('ko-KR',{maximumFractionDigits:1})}조원`;
const volume = (value, unit='주') => valueOrNull(value) === null ? '-' : unit==='억' ? `${comma(value)}억원` : `${comma(Math.round(Number(value)/1000))}천주`;
const flow = (value, unit='주') => valueOrNull(value) === null ? '-' : unit==='억' ? `${signed(value)}억원` : `${signed(Math.round(Number(value)/1000))}천주`;
const esc = value => String(value??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));

function rowspans(rows,key){const spans={};let start=0;while(start<rows.length){let end=start+1;while(end<rows.length&&rows[end][key]===rows[start][key])end++;spans[start]=end-start;start=end;}return spans;}

function renderIndicators(){
  const spans=rowspans(report.indicators,'group');
  document.querySelector('#indicatorRows').innerHTML=report.indicators.map((row,i)=>{
    const kind=row.group==='환율'?'fx':'index'; const unit=row.group==='국내'?'억':'주';
    return `<tr class="${spans[i]?'group-start':''}">${spans[i]?`<td class="group" rowspan="${spans[i]}">${esc(row.group)}</td>`:''}<td class="name">${esc(row.name)}</td><td>${price(row.previous,kind)}</td><td>${price(row.current,kind)}</td><td>${row.group==='국내'?marketCap(row.market_cap):'-'}</td><td class="${signClass(row.change)}">${signed(row.change,kind==='stock'?0:2)}</td><td class="${signClass(row.change_rate)}">${rate(row.change_rate)}</td><td>${row.group==='국내'?volume(row.volume,'억'):'-'}</td><td class="${signClass(row.foreign)}">${flow(row.foreign,unit)}</td><td class="${signClass(row.institution)}">${flow(row.institution,unit)}</td><td class="${signClass(row.other)}">${flow(row.other,unit)}</td></tr>`;
  }).join('');
}

function renderStocks(){
  const spans=rowspans(report.stocks,'sector');
  document.querySelector('#stockRows').innerHTML=report.stocks.map((row,i)=>`<tr class="${spans[i]?'group-start':''} ${row.highlight?'highlight':''}">${spans[i]?`<td class="group" rowspan="${spans[i]}">${esc(row.sector)}</td>`:''}<td class="name">${esc(row.name)}</td><td>${price(row.previous)}</td><td>${price(row.current)}</td><td>${marketCap(row.market_cap)}</td><td class="${signClass(row.change)}">${signed(row.change)}</td><td class="${signClass(row.change_rate)}">${rate(row.change_rate)}</td><td>${volume(row.volume)}</td><td class="${signClass(row.foreign)}">${flow(row.foreign)}</td><td class="${signClass(row.institution)}">${flow(row.institution)}</td><td class="${signClass(row.other)}">${flow(row.other)}</td></tr>`).join('');
}

function referenceBox(category, title=category){
  const items=report.telegram?.[category]||[];
  const body=items.length?items.map(item=>`<div class="reference-item"><div class="reference-meta">${esc((item.date||'').replace('T',' '))} / ${esc(item.channel||'-')}</div><div class="reference-text">${item.link?`<a href="${esc(item.link)}" target="_blank" rel="noopener">${esc(item.text)}</a>`:esc(item.text)}</div></div>`).join(''):'<div class="reference-empty">일치하는 Telegram 원문이 없습니다.</div>';
  return `<div class="reference-box"><div class="reference-title">[${esc(title)} 관련 Telegram]</div>${body}</div>`;
}

function renderComments(){
  document.querySelector('#commentary').innerHTML=commentOrder.map(([key,label])=>`<div class="comment-block"><div class="comment-title">${label}</div><div class="comment-body"><div class="comment-view" data-comment-view="${key}">${esc(report.comments?.[key]||'')}</div><textarea data-comment-input="${key}" rows="3" placeholder="${label} 시황을 직접 작성하세요.">${esc(report.comments?.[key]||'')}</textarea></div></div>`).join('');
  document.querySelector('[data-comment-view="USD/KRW"]').textContent=report.comments?.['USD/KRW']||'';
  document.querySelector('[data-comment-input="USD/KRW"]').value=report.comments?.['USD/KRW']||'';
  document.querySelector('#fxReferences').innerHTML=referenceBox('환율','환율');
}

function telegramCard(item, showStocks=false){
  const date=(item.date||'').replace('T',' ').slice(0,16);
  const stocks=showStocks&&item.stocks?.length?`<div class="telegram-stocks">관련종목: ${item.stocks.map(esc).join(' / ')}</div>`:'';
  const link=item.link?`<a class="telegram-link" href="${esc(item.link)}" target="_blank" rel="noopener">원문 보기 ↗</a>`:'';
  return `<article class="telegram-card"><div class="telegram-card-head"><span class="telegram-source">[${esc(item.source||item.channel||'-')}]</span><time class="telegram-time">${esc(date)}</time></div>${stocks}<p class="telegram-excerpt">${esc(item.excerpt||'')}</p>${link}</article>`;
}
function renderTelegramFeed(){
  const feed=report.telegram_feed||{closing:[],stock_news:[]};
  document.querySelector('#closingMarket').innerHTML=feed.closing?.length?feed.closing.map(item=>telegramCard(item)).join(''):'<div class="telegram-empty">선택한 날짜의 마감시황 게시물이 없습니다.</div>';
  document.querySelector('#stockNews').innerHTML=feed.stock_news?.length?feed.stock_news.map(item=>telegramCard(item,true)).join(''):'<div class="telegram-empty">선택한 날짜의 관심종목 뉴스가 없습니다.</div>';
}

function render(){
  document.querySelector('#reportDate').textContent=report.date.replaceAll('-','.');
  renderMarketStatus();
  renderIndicators();renderStocks();renderComments();renderTelegramFeed();
  document.body.classList.toggle('editing',editing);
  document.querySelector('#editButton').textContent=editing?'편집 취소':'편집';
  document.querySelector('#saveButton').disabled=!editing;
}

function renderMarketStatus(){
  const element=document.querySelector('#marketStatus');
  const timestamp=report.updatedAt||report.updated_at;
  const parts=new Intl.DateTimeFormat('en-US',{timeZone:'Asia/Seoul',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date());
  const value=Object.fromEntries(parts.map(part=>[part.type,part.value]));
  const today=`${value.year}-${value.month}-${value.day}`;
  const display=timestamp?timestamp.slice(0,16).replace('T',' ').replaceAll('-','.'):'정상 갱신 기록 없음';
  const current=report.status==='success'&&timestamp&&timestamp.slice(0,10)===today;
  element.textContent=current?`● 데이터 정상 · ${display} 갱신`:`● 데이터 갱신 확인 필요 · ${timestamp?`마지막 정상 갱신 ${display}`:display}`;
  element.classList.toggle('status-ok',Boolean(current));
  element.classList.toggle('status-warn',!current);
  document.querySelector('#updatedAt').textContent='';
}

async function api(path,payload=null){
  const options=payload?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)}:{};
  const response=await fetch(path,options);const result=await response.json();
  if(!result.ok)throw new Error(result.error||'요청 실패');return result.report;
}
function status(message,error=false){const el=document.querySelector('#actionStatus');el.textContent=message;el.style.color=error?'#ffb6b6':'#dce5ef';}
async function load(){try{report=await api('/api/report');render();}catch(error){status(error.message,true);}}
async function update(path,label){status(`${label} 중...`);toggleBusy(true);try{report=await api(path,{date:report.date});render();status(`${label} 완료`);}catch(error){status(error.message,true);}finally{toggleBusy(false);}}
function toggleBusy(value){document.querySelectorAll('.admin-bar button').forEach(button=>button.disabled=value||(button.id==='saveButton'&&!editing));}
function collectComments(){document.querySelectorAll('[data-comment-input]').forEach(input=>{report.comments[input.dataset.commentInput]=input.value.trim();});}
async function save(){collectComments();status('저장 중...');try{report=await api('/api/report/save',report);editing=false;render();status(`${report.date}.json 저장 완료`);}catch(error){status(error.message,true);}}

function indicatorTsv(){return [['대분류','구분','전일','당일','시총','전일대비','%','거래량','외국인','기관','기타'],...report.indicators.map(r=>[r.group,r.name,r.previous??'',r.current??'',r.market_cap??'',r.change??'',r.change_rate??'',r.volume??'',r.foreign??'',r.institution??'',r.other??''])];}
function stockTsv(){return [['업종','종목명','전일','당일','시총','전일대비','%','거래량','외국인','기관','기타'],...report.stocks.map(r=>[r.sector,r.name,r.previous??'',r.current??'',r.market_cap??'',r.change??'',r.change_rate??'',r.volume??'',r.foreign??'',r.institution??'',r.other??''])];}
const toTsv=rows=>rows.map(row=>row.join('\t')).join('\n');
function commentaryText(){collectComments();return ['증권시장 동향 - '+report.date.replaceAll('-','.'),'','○ 미국증시',report.comments['미국증시']||'','', '○ 국내증시',report.comments['국내증시']||'',`- (방산주) ${report.comments['방산']||''}`,`- (현대로템) ${report.comments['현대로템']||''}`,`- (반도체) ${report.comments['반도체']||''}`,'',`○ USD 환율 동향`,report.comments['USD/KRW']||''].join('\n');}
async function copy(text,label){try{await navigator.clipboard.writeText(text);}catch{const area=document.createElement('textarea');area.value=text;document.body.append(area);area.select();document.execCommand('copy');area.remove();}status(`${label} 완료`);}

document.querySelector('#marketUpdate').onclick=()=>update('/api/market/update','시장 데이터 업데이트');
document.querySelector('#telegramUpdate').onclick=()=>update('/api/telegram/update','Telegram 업데이트');
document.querySelector('#editButton').onclick=()=>{editing=!editing;render();};
document.querySelector('#saveButton').onclick=save;
document.querySelector('#copyTable').onclick=()=>copy(`${toTsv(indicatorTsv())}\n\n${toTsv(stockTsv())}`,'표 복사');
document.querySelector('#copyCommentary').onclick=()=>copy(commentaryText(),'시황 복사');
document.querySelector('#copyAll').onclick=()=>copy(`${toTsv(indicatorTsv())}\n\n${toTsv(stockTsv())}\n\n${commentaryText()}`,'전체 복사');

function unlock(){
  localStorage.setItem('dailyTrendUnlocked','true');
  document.body.classList.remove('app-locked');
  document.querySelector('#unlockError').textContent='';
  load();
}
document.querySelector('#unlockForm').addEventListener('submit',event=>{
  event.preventDefault();
  if(document.querySelector('#unlockPassword').value==='260616')unlock();
  else{document.querySelector('#unlockError').textContent='비밀번호가 맞지 않습니다.';document.querySelector('#unlockPassword').select();}
});
if(localStorage.getItem('dailyTrendUnlocked')==='true')unlock();
