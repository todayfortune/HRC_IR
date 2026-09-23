const stocks = [
  {code:'005930',name:'삼성전자',price:74200,change:1.23,volume:12845021,foreign:328410,signal:'관심'},
  {code:'000660',name:'SK하이닉스',price:186400,change:2.08,volume:4421568,foreign:218905,signal:'강세'},
  {code:'035420',name:'NAVER',price:214500,change:-0.69,volume:910224,foreign:-45870,signal:'관망'},
  {code:'005380',name:'현대차',price:245000,change:0.82,volume:1084611,foreign:71520,signal:'관심'},
  {code:'051910',name:'LG화학',price:391500,change:-1.14,volume:382991,foreign:-22590,signal:'관망'},
  {code:'247540',name:'에코프로비엠',price:178600,change:3.18,volume:1268320,foreign:55310,signal:'강세'}
];
const briefs=[['15:24','반도체 대형주 중심 외국인 순매수 확대','수급'],['14:48','원/달러 환율 장중 변동성 축소','매크로'],['13:35','2차전지 업종 거래량 전일 대비 증가','거래량'],['11:10','코스피 기관 매수 전환 감지','수급']];
const fmt=n=>new Intl.NumberFormat('ko-KR').format(n);
const sign=n=>n>0?'+':'';
function render(){
  document.querySelector('#stockRows').innerHTML=stocks.map(s=>`<tr><td class="stock-name"><strong>${s.name}</strong><span>${s.code}</span></td><td>${fmt(s.price)}원</td><td class="${s.change>=0?'up':'down'}">${sign(s.change)}${s.change.toFixed(2)}%</td><td>${fmt(s.volume)}</td><td class="${s.foreign>=0?'up':'down'}">${sign(s.foreign)}${fmt(s.foreign)}</td><td><span class="signal ${s.signal==='관망'?'watch':''}">${s.signal}</span></td></tr>`).join('');
  const total=stocks.reduce((a,s)=>a+s.volume,0);
  document.querySelector('#metrics').innerHTML=[['KOSPI','2,748.56','+0.67%','up'],['KOSDAQ','862.31','-0.14%','down'],['USD / KRW','1,334.80','-2.10','down'],['관심종목 거래량',fmt(total),'6개 종목','']].map(m=>`<div class="metric"><span>${m[0]}</span><strong>${m[1]}</strong><small class="${m[3]}">${m[2]}</small></div>`).join('');
  document.querySelector('#briefs').innerHTML=briefs.map(b=>`<article class="brief"><time>${b[0]}</time><p>${b[1]}</p><tag># ${b[2]}</tag></article>`).join('');
}
function excelText(){const rows=[['종목명','종목코드','현재가','등락률(%)','거래량','외인 순매수','시그널'],...stocks.map(s=>[s.name,s.code,s.price,s.change,s.volume,s.foreign,s.signal])];return rows.map(row=>row.join('\t')).join('\n');}
async function copyExcel(){
  const status=document.querySelector('#copyStatus');
  try{await navigator.clipboard.writeText(excelText());status.textContent='✓ Excel에 바로 붙여넣을 수 있도록 6개 종목을 복사했습니다.';}
  catch{const area=document.createElement('textarea');area.value=excelText();document.body.append(area);area.select();document.execCommand('copy');area.remove();status.textContent='✓ 표 데이터를 복사했습니다.';}
  status.classList.add('show');setTimeout(()=>status.classList.remove('show'),2800);
}
document.querySelector('#copyButton').addEventListener('click',copyExcel);
document.querySelector('#refreshButton').addEventListener('click',render);
document.querySelector('#now').textContent=new Intl.DateTimeFormat('ko-KR',{dateStyle:'long',timeStyle:'short'}).format(new Date());
render();
