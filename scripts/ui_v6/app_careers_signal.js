function spCareersFacts(x){return facts(x,'careers_page')}
function spJobFacts(x){return facts(x,'job_posting')}
function spCareersUrl(f){let v=f?.value;if(v&&typeof v==='object')return v.url||v.href||'';return typeof v==='string'&&/^https?:\/\//i.test(v)?v:''}
const spCareersBaseFilterPass=filterPass;
filterPass=function(x){if(activeFilter==='careers')return spCareersFacts(x).length>0;return spCareersBaseFilterPass(x)};
function spCareersInstallFilter(){let filters=$('#filters');if(!filters||filters.querySelector('[data-filter="careers"]'))return;let b=document.createElement('button');b.className='filter';b.dataset.filter='careers';b.type='button';b.textContent='Careers';b.onclick=()=>{activeFilter='careers';$$('.filter').forEach(x=>x.classList.toggle('active',x===b));renderList()};let changed=filters.querySelector('[data-filter="changes"]');filters.insertBefore(b,changed||null)}
function spCareersEnhanceList(){ $$('.company-row').forEach(row=>{let x=companyFor(row.dataset.org),badges=row.querySelector('.row-badges');if(!x||!badges||!spCareersFacts(x).length||badges.querySelector('.careers-badge'))return;badges.insertAdjacentHTML('beforeend','<span class="dot-badge on careers-badge">careers</span>')}) }
function spCareersEnhanceProfile(){let x=selectedCompany(),area=$('#hiring_and_public_activity');if(!x||!area||area.querySelector('.careers-boundary'))return;let careers=spCareersFacts(x);if(!careers.length)return;let jobs=spJobFacts(x),first=careers[0],url=spCareersUrl(first),evidence=uniqEvidence(careers.flatMap(f=>f.evidence||[]));let note=document.createElement('div');note.className='no-data careers-boundary';note.innerHTML=`<strong>Careers surface found.</strong> A verified company-owned careers page is published.${jobs.length?` ${jobs.length} qualified job posting${jobs.length===1?' is':'s are'} also published in the current evidence.`:' This does not establish an active vacancy.'}${url?` <a href="${esc(url)}" target="_blank" rel="noreferrer">Open careers page ↗</a>`:''}<div class="source-mini">${sourceButtons(evidence,'Careers evidence')}</div>`;let head=area.querySelector('.area-head');head?.insertAdjacentElement('afterend',note);bindEvidenceButtons(note)}
const spCareersBaseRenderList=renderList;
renderList=function(){spCareersBaseRenderList();spCareersEnhanceList()};
const spCareersBaseRenderProfile=renderProfile;
renderProfile=function(){spCareersBaseRenderProfile();spCareersEnhanceProfile()};
const spCareersBaseAnswerQuestion=answerQuestion;
answerQuestion=function(q){let x=selectedCompany(),n=norm(q);if(x&&/(hiring|hire|job|jobs|vacanc|career)/.test(n)){let jobs=spJobFacts(x),careers=spCareersFacts(x);if(jobs.length)return {text:`Current evidence includes ${jobs.length} qualified job posting${jobs.length===1?'':'s'}.${careers.length?' A verified company-owned careers page is also published.':''}`,evidence:uniqEvidence([...jobs,...careers].flatMap(f=>f.evidence||[]))};if(careers.length)return {text:'A verified company-owned careers page is published, but the current evidence does not establish an active vacancy.',evidence:uniqEvidence(careers.flatMap(f=>f.evidence||[]))};return {text:'No qualified job posting or verified company-owned careers page is published in the current evidence.',evidence:[]}}return spCareersBaseAnswerQuestion(q)};
function spCareersInstallAskSuggestion(){let box=$('#suggestions');if(!box||box.querySelector('[data-question="Are they hiring?"]'))return;let b=document.createElement('button');b.type='button';b.dataset.question='Are they hiring?';b.textContent='Hiring evidence';b.onclick=()=>{$('#askInput').value=b.dataset.question;renderAnswer(b.dataset.question)};box.appendChild(b)}
spCareersInstallFilter();
spCareersInstallAskSuggestion();
renderList();
renderProfile();
