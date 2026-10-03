const SP_DECISION_ITEMS=[
  ['what_is_this_company','Company'],
  ['what_does_it_do','What it does'],
  ['how_big_is_it','Size'],
  ['who_runs_it','Leadership'],
  ['hiring','Hiring'],
  ['digital_footprint','Digital footprint'],
];
function spDecisionBriefCards(synth){
  const brief=synth?.decisionBrief||{};
  return SP_DECISION_ITEMS.map(([key,label])=>{
    const item=brief[key];
    if(!item||!String(item.text||'').trim())return '';
    const dates=Array.isArray(item.dates)?item.dates:[];
    const temporal=dates.length?`<div class="meta">${dates.map(esc).join(' · ')}</div>`:'';
    return `<article class="brief decision-brief-card" data-decision-key="${esc(key)}"><h3>${esc(label)}</h3><p>${esc(item.text)}</p>${temporal}<div class="source-mini">${sourceButtons(item.evidence||[],'Evidence')}</div></article>`;
  }).join('');
}
const spDecisionBaseRenderProfile=renderProfile;
renderProfile=function(){
  spDecisionBaseRenderProfile();
  const x=selectedCompany(),grid=$('#company-brief .brief-grid');
  if(!x||!grid)return;
  const cards=spDecisionBriefCards(x.synthesis||{});
  if(!cards)return;
  grid.innerHTML=cards;
  grid.setAttribute('aria-label','Decision brief');
  bindEvidenceButtons(grid);
};
