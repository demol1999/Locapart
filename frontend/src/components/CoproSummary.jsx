import React, { useEffect, useState } from 'react';

export default function CoproSummary({ coproId, navigate }) {
  const [copro, setCopro] = useState(null);
  useEffect(() => {
    import('../services/api').then(({ default: apiClient }) => {
      apiClient.get(`/copros/${coproId}`)
        .then(res => setCopro(res.data))
        .catch(() => setCopro(null));
    });
  }, [coproId]);

  if (!copro) return (
    <div style={{border:'1px solid #1976d2', borderRadius:8, padding:20, marginBottom:32, background:'#f5faff'}}>
      <strong>Copropriété associée :</strong> <br/>
      <span style={{color:'red'}}>Impossible de charger la copropriété</span>
    </div>
  );

  return (
    <div style={{border:'1px solid #1976d2', borderRadius:8, padding:20, marginBottom:32, background:'#f5faff'}}>
      <strong>Copropriété associée :</strong> <br/>
      <div><b>Nom :</b> {copro.nom || '-'}</div>
      <div><b>Adresse :</b> {copro.adresse_rue || ''}, {copro.adresse_code_postal || ''} {copro.adresse_ville || ''}</div>
      <button
        style={{marginTop:12, background:'#1976d2',color:'white',padding:'6px 18px',border:'none',borderRadius:4,cursor:'pointer'}}
        onClick={() => navigate(`/copros/${coproId}`)}
      >
        Modifier / Voir la fiche copropriété
      </button>
    </div>
  );
}
