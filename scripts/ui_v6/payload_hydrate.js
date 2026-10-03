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
      if(!item||Array.isArray(item)||typeof item!=='object'||!Array.isArray(item.evidenceRefs))return;
      const meta=item.evidenceMeta||{};
      item.evidence=item.evidenceRefs.map(id=>pool[id]?{...pool[id],...(meta[id]||{})}:null).filter(Boolean);
      delete item.evidenceRefs;
      delete item.evidenceMeta;
    });
  });
  return companies;
}
