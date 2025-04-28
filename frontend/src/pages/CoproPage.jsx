import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';

export default function CoproPage() {
  const { coproId } = useParams();
  const navigate = useNavigate();
  const [copro, setCopro] = useState(null);
  const [syndicat, setSyndicat] = useState(null);
  const [syndicats, setSyndicats] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editMode, setEditMode] = useState(false);
  const [editForm, setEditForm] = useState({});
  const [showSyndicatModal, setShowSyndicatModal] = useState(false);
  const [syndicatCreateMode, setSyndicatCreateMode] = useState(false);
  // Champs du modèle SyndicatCopro (hors id)
const syndicatFields = [
  'statut_juridique','date_creation','reglement_copro','carnet_entretien','nom_syndic','type_syndic','societe_syndic','date_derniere_ag','assurance_compagnie','assurance_num_police','assurance_validite','procedures_judiciaires','procedures_details','budget_annuel_previsionnel','charges_annuelles_par_lot','charges_speciales','emprunt_collectif','emprunt_montant','emprunt_echeance','taux_impayes_charges','fonds_roulement','fonds_travaux','travaux_votes','travaux_en_cours'
];
const syndicatDefaults = Object.fromEntries(syndicatFields.map(f => [f, ['reglement_copro','carnet_entretien','procedures_judiciaires','emprunt_collectif'].includes(f) ? false : '']));
const [syndicatForm, setSyndicatForm] = useState(syndicatDefaults);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    import('../services/api').then(async ({ default: apiClient }) => {
      try {
        const coproRes = await apiClient.get(`/copros/${coproId}`);
        setCopro(coproRes.data);
        setEditForm(coproRes.data);
        try {
          const syndicatRes = await apiClient.get(`/copros/${coproId}/syndicat`);
          setSyndicat(syndicatRes.data);
        } catch {
          setSyndicat(null);
        }
        // Liste des syndicats pour ajout
        const syndicatsRes = await apiClient.get('/syndicats_copro/');
        setSyndicats(syndicatsRes.data);
      } catch (err) {
        setCopro(null);
        setError("Erreur de chargement");
      } finally {
        setLoading(false);
      }
    });
  }, [coproId]);

  const handleEdit = () => setEditMode(true);
  const handleCancel = () => {
    setEditForm(copro);
    setEditMode(false);
    setError(null);
  };
  const handleEditChange = e => {
    const { name, value, type, checked } = e.target;
    setEditForm(f => ({ ...f, [name]: type === 'checkbox' ? checked : value }));
  };
  const handleSave = async () => {
    setLoading(true);
    setError(null);
    import('../services/api').then(async ({ default: apiClient }) => {
      try {
        await apiClient.put(`/copros/${coproId}`, editForm);
        setCopro(editForm);
        setEditMode(false);
      } catch (err) {
        setError("Erreur lors de la sauvegarde");
      } finally {
        setLoading(false);
      }
    });
  };
  const handleDelete = async () => {
    if (!window.confirm('Supprimer définitivement cette copropriété ?')) return;
    setLoading(true);
    setError(null);
    import('../services/api').then(async ({ default: apiClient }) => {
      try {
        // On récupère l'immeuble avant suppression pour rediriger
        const buildingId = copro.building_id;
        await apiClient.delete(`/copros/${coproId}`);
        if (buildingId) navigate(`/buildings/${buildingId}`);
        else navigate('/buildings');
      } catch (err) {
        setError("Erreur lors de la suppression");
      } finally {
        setLoading(false);
      }
    });
  };
  // Ajout ou association d'un syndicat
  const handleAddSyndicat = async (syndicatId) => {
    setLoading(true);
    setError(null);
    import('../services/api').then(async ({ default: apiClient }) => {
      try {
        await apiClient.put(`/copros/${coproId}`, { ...copro, syndicat_copro_id: syndicatId });
        setSyndicat(syndicats.find(s => s.id === Number(syndicatId)));
        setShowSyndicatModal(false);
      } catch (err) {
        setError("Erreur lors de l'association du syndicat");
      } finally {
        setLoading(false);
      }
    });
  };
  const handleCreateSyndicat = async () => {
    setLoading(true);
    setError(null);
    import('../services/api').then(async ({ default: apiClient }) => {
      try {
        const res = await apiClient.post('/syndicats_copro/', syndicatForm);
        await handleAddSyndicat(res.data.id);
        setSyndicatCreateMode(false);
        setSyndicatForm({ nom: '', adresse: '' });
      } catch (err) {
        setError("Erreur lors de la création du syndicat");
      } finally {
        setLoading(false);
      }
    });
  };


  useEffect(() => {
    import('../services/api').then(({ default: apiClient }) => {
      apiClient.get(`/copros/${coproId}`)
        .then(res => setCopro(res.data))
        .catch(() => setCopro(null));
      apiClient.get(`/copros/${coproId}/syndicat`)
        .then(res => setSyndicat(res.data))
        .catch(() => setSyndicat(null))
        .finally(() => setLoading(false));
    });
  }, [coproId]);

  if (loading) return <div style={{padding: 32}}>Chargement...</div>;
  if (!copro) return <div style={{padding: 32}}>Copropriété introuvable</div>;

  return (
    <div style={{ maxWidth: 900, margin: '0 auto', padding: 32 }}>
      <button onClick={() => navigate(-1)} style={{marginBottom: 24, background: '#eee', border: 'none', borderRadius: 4, padding: '8px 18px', cursor: 'pointer', fontWeight: 'bold'}}>← Retour</button>
      <div style={{display:'flex', justifyContent:'space-between', alignItems:'center'}}>
        <h2 style={{marginBottom:0}}>Copropriété : {copro.nom}</h2>
        <div>
          {!editMode && <button onClick={handleEdit} style={{marginRight:12, background:'#1976d2',color:'white',border:'none',borderRadius:4,padding:'8px 18px',fontWeight:'bold',cursor:'pointer'}}>Modifier</button>}
          {!editMode && <button onClick={handleDelete} style={{background:'#e53935',color:'white',border:'none',borderRadius:4,padding:'8px 18px',fontWeight:'bold',cursor:'pointer'}}>Supprimer</button>}
        </div>
      </div>
      {error && <div style={{color:'red',margin:'16px 0'}}>{error}</div>}

      <form onSubmit={e => {e.preventDefault(); handleSave();}} style={{margin:'32px 0', background:'#f7f7fa', borderRadius:12, padding:24, boxShadow:'0 2px 8px #0001'}}>
  <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:20}}>
    {Object.keys(editForm).filter(key => key !== 'id').map(key => {
      // Détection du type
      const value = editForm[key];
      const isBool = typeof value === 'boolean' || ['ascenseur','clim_centralisee','eau_chaude_collective','rt2012_re2020','accessibilite_pmr','gardien','local_velos','parkings_ext','parkings_int','caves','espaces_verts','jardins_partages','piscine','salle_sport','aire_jeux','salle_reunion','audit_energetique','panneaux_solaires','bornes_recharge'].includes(key);
      const isNumber = typeof value === 'number' || [
        'annee_construction','nb_batiments','nb_lots_total','nb_lots_principaux','nb_lots_secondaires','surface_totale_m2','nb_etages','nb_ascenseurs','isolation_annee','nb_parkings_ext','nb_parkings_int','nb_caves'
      ].includes(key);
      // Label lisible
      const label = key.replace(/_/g,' ').replace(/\b\w/g, l => l.toUpperCase());
      return (
        <div key={key} style={{minWidth:180}}>
          <label>{label}</label>
          {isBool ? (
            <input type="checkbox" disabled={!editMode} name={key} checked={!!editForm[key]} onChange={handleEditChange} className="form-check-input" style={{marginLeft:8}} />
          ) : isNumber ? (
            <input type="number" disabled={!editMode} name={key} value={editForm[key]||''} onChange={handleEditChange} className="form-control" />
          ) : (
            <input type="text" disabled={!editMode} name={key} value={editForm[key]||''} onChange={handleEditChange} className="form-control" />
          )}
        </div>
      );
    })}
  </div>
  {editMode && (
    <div style={{marginTop:32,display:'flex',gap:16}}>
      <button type="button" onClick={handleCancel} style={{background:'#eee',color:'#222',border:'none',borderRadius:4,padding:'8px 18px',fontWeight:'bold',cursor:'pointer'}}>Annuler</button>
      <button type="submit" style={{background:'#1976d2',color:'white',border:'none',borderRadius:4,padding:'8px 18px',fontWeight:'bold',cursor:'pointer'}}>Enregistrer</button>
    </div>
  )}
</form>


      <h3 style={{marginTop:32}}>Syndicat de copropriété</h3>
      {syndicat ? (
        <div style={{background:'#e3f2fd',padding:16,borderRadius:8,marginBottom:16}}>
          <strong>{syndicat.nom}</strong><br/>
          {syndicat.adresse}
        </div>
      ) : (
        <div style={{marginBottom:16}}>
          Aucun syndicat renseigné.<br/>
          <button onClick={()=>setShowSyndicatModal(true)} style={{marginTop:8,background:'#1976d2',color:'white',border:'none',borderRadius:4,padding:'8px 18px',fontWeight:'bold',cursor:'pointer'}}>Ajouter un syndicat</button>
        </div>
      )}
      {/* Modal ajout/association syndicat */}
      {showSyndicatModal && (
        <div style={{position:'fixed',top:0,left:0,width:'100vw',height:'100vh',background:'#0008',zIndex:1000,display:'flex',alignItems:'center',justifyContent:'center'}}>
          <div style={{background:'#fff',padding:32,borderRadius:12,minWidth:350}}>
            <h4>Associer ou créer un syndicat</h4>
            {!syndicatCreateMode ? (
              <>
                <select style={{width:'100%',marginBottom:16}} onChange={e=>handleAddSyndicat(e.target.value)} defaultValue="">
                  <option value="" disabled>Choisir un syndicat existant...</option>
                  {syndicats.map(s => <option key={s.id} value={s.id}>{s.nom}</option>)}
                </select>
                <button onClick={()=>{ setShowSyndicatModal(false); navigate(`/syndicats_copro/create/${coproId}`); }} style={{background:'#1976d2',color:'white',border:'none',borderRadius:4,padding:'8px 18px',fontWeight:'bold',cursor:'pointer'}}>Créer un nouveau syndicat</button>
                <button onClick={()=>setShowSyndicatModal(false)} style={{marginLeft:12,background:'#eee',color:'#222',border:'none',borderRadius:4,padding:'8px 18px',fontWeight:'bold',cursor:'pointer'}}>Annuler</button>
              </>
            ) : (
              <>
                <form onSubmit={e => {e.preventDefault(); handleCreateSyndicat();}}>
  <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:16}}>
    {syndicatFields.map(field => {
      const isBool = ['reglement_copro','carnet_entretien','procedures_judiciaires','emprunt_collectif'].includes(field);
      const isNumber = ['budget_annuel_previsionnel','charges_annuelles_par_lot','charges_speciales','emprunt_montant','taux_impayes_charges','fonds_roulement','fonds_travaux'].includes(field);
      const label = field.replace(/_/g,' ').replace(/\b\w/g, l => l.toUpperCase());
      return (
        <div key={field}>
          <label>{label}</label>
          {isBool ? (
            <input type="checkbox" name={field} checked={!!syndicatForm[field]} onChange={e=>setSyndicatForm(f=>({...f,[field]:e.target.checked}))} className="form-check-input" style={{marginLeft:8}} />
          ) : isNumber ? (
            <input type="number" name={field} value={syndicatForm[field]||''} onChange={e=>setSyndicatForm(f=>({...f,[field]:e.target.value}))} className="form-control" />
          ) : (
            <input type="text" name={field} value={syndicatForm[field]||''} onChange={e=>setSyndicatForm(f=>({...f,[field]:e.target.value}))} className="form-control" />
          )}
        </div>
      );
    })}
  </div>
  <div style={{marginTop:24,display:'flex',gap:12}}>
    <button type="submit" style={{background:'#1976d2',color:'white',border:'none',borderRadius:4,padding:'8px 18px',fontWeight:'bold',cursor:'pointer'}}>Créer et associer</button>
    <button type="button" onClick={()=>setSyndicatCreateMode(false)} style={{background:'#eee',color:'#222',border:'none',borderRadius:4,padding:'8px 18px',fontWeight:'bold',cursor:'pointer'}}>Retour</button>
  </div>
</form>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

