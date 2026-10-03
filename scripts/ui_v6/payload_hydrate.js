function hydrateSignalpostPayload(raw){
  if(Array.isArray(raw))return raw;
  const pool=raw?.evidence||{};
  const companies=Array.isArray(raw?.companies)?raw.companies:[];
  companies.forEach(company=>{
    Object.values(company?.areas||{}).flat().forEach(fact=>{
      if(Array.isArray(fact?.evidenceRefs)){
        fact.evidence=fact.evidenceRefs.map(id=>pool[id]).filter(Boolean);
        delete fact.evidenceRefs;
      }
    });
    (company?.synthesis?.sections||[]).forEach(section=>{
      if(Array.isArray(section?.sourceRefs)){
        section.sources=section.sourceRefs.map(id=>pool[id]).filter(Boolean);
        delete section.sourceRefs;
      }
    });
    Object.values(company?.synthesis?.decisionBrief||{}).forEach(item=>{
      if(!item||Array.isArray(item)||typeof item!=='object')return;
      if(Array.isArray(item.e)){
        item.evidence=item.e.map(id=>pool[id]).filter(Boolean);
        delete item.e;
      }
      if(Array.isArray(item.d)){
        item.dates=item.d;
        delete item.d;
      }
    });
  });
  return companies;
}
