import React, { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

// Champs du modèle SyndicatCopro (hors id et copro_id)
const syndicatFields = [
  'statut_juridique','date_creation','reglement_copro','carnet_entretien','nom_syndic','type_syndic','societe_syndic','date_derniere_ag','assurance_compagnie','assurance_num_police','assurance_validite','procedures_judiciaires','procedures_details','budget_annuel_previsionnel','charges_annuelles_par_lot','charges_speciales','emprunt_collectif','emprunt_montant','emprunt_echeance','taux_impayes_charges','fonds_roulement','fonds_travaux','travaux_votes','travaux_en_cours'
];
const syndicatDefaults = Object.fromEntries(syndicatFields.map(f => [f, ['reglement_copro','carnet_entretien','procedures_judiciaires','emprunt_collectif'].includes(f) ? false : '']));

export default function SyndicatCreatePage() {
  const navigate = useNavigate();
  const { coproId } = useParams();
  const [form, setForm] = useState(syndicatDefaults);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleChange = e => {
    const { name, value, type, checked } = e.target;
    setForm(f => ({ ...f, [name]: type === 'checkbox' ? checked : value }));
  };

  const handleSubmit = async e => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    import('../services/api').then(async ({ default: apiClient }) => {
      try {
        // Création du syndicat (POST sur /syndicats_copro/ avec tous les champs)
        const cleanedForm = Object.fromEntries(
  Object.entries({ ...form, copro_id: Number(coproId) })
    .filter(([_, v]) => v !== '' && v !== undefined)
);
const res = await apiClient.post(`/copros/${coproId}/syndicat`, cleanedForm);
        const syndicatId = res.data.id;
        // Lier à la copropriété si coproId fourni
        if (coproId) {
          await apiClient.put(`/copros/${coproId}`, { syndicat_copro_id: syndicatId });
          navigate(`/copros/${coproId}`);
        } else {
          navigate('/copros');
        }
      } catch (err) {
        setError("Erreur lors de la création du syndicat");
      } finally {
        setLoading(false);
      }
    });
  };

  return (
    <div style={{ maxWidth: 700, margin: '0 auto', padding: 32 }}>
      <button onClick={() => navigate(-1)} style={{marginBottom: 24, background: '#eee', border: 'none', borderRadius: 4, padding: '8px 18px', cursor: 'pointer', fontWeight: 'bold'}}>← Retour</button>
      <h2>Créer un nouveau syndicat de copropriété</h2>
      {error && <div style={{color:'red',margin:'16px 0'}}>{error}</div>}
      <form onSubmit={handleSubmit} style={{margin:'32px 0', background:'#f7f7fa', borderRadius:12, padding:24, boxShadow:'0 2px 8px #0001'}}>
        <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:20}}>
          {syndicatFields.map(field => {
            const isBool = ['reglement_copro','carnet_entretien','procedures_judiciaires','emprunt_collectif'].includes(field);
            const isNumber = ['budget_annuel_previsionnel','charges_annuelles_par_lot','charges_speciales','emprunt_montant','taux_impayes_charges','fonds_roulement','fonds_travaux'].includes(field);
            const label = field.replace(/_/g,' ').replace(/\b\w/g, l => l.toUpperCase());
            return (
              <div key={field}>
                <label>{label}</label>
                {isBool ? (
                  <input type="checkbox" name={field} checked={!!form[field]} onChange={handleChange} className="form-check-input" style={{marginLeft:8}} />
                ) : isNumber ? (
                  <input type="number" name={field} value={form[field]||''} onChange={handleChange} className="form-control" />
                ) : (
                  <input type="text" name={field} value={form[field]||''} onChange={handleChange} className="form-control" />
                )}
              </div>
            );
          })}
        </div>
        <div style={{marginTop:32,display:'flex',gap:16}}>
          <button type="submit" disabled={loading} style={{background:'#1976d2',color:'white',border:'none',borderRadius:4,padding:'8px 18px',fontWeight:'bold',cursor:'pointer'}}>Créer le syndicat</button>
        </div>
      </form>
    </div>
  );
}
