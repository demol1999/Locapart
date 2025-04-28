import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

export default function CoproCreatePage() {
  const navigate = useNavigate();
  const location = useLocation();

  // Récupère le buildingId depuis la query string ou le state
  const searchParams = new URLSearchParams(location.search);
  const buildingId = searchParams.get('buildingId') || location.state?.buildingId || null;

  // Tous les champs importants de la copropriété
  const [form, setForm] = useState({
    nom: '',
    adresse_rue: '',
    adresse_code_postal: '',
    adresse_ville: '',
    annee_construction: '',
    nb_batiments: '',
    nb_lots_total: '',
    nb_lots_principaux: '',
    nb_lots_secondaires: '',
    surface_totale_m2: '',
    type_construction: '',
    nb_etages: '',
    ascenseur: false,
    nb_ascenseurs: '',
    chauffage_collectif_type: '',
    chauffage_individuel_type: '',
    clim_centralisee: false,
    eau_chaude_collective: false,
    isolation_thermique: '',
    isolation_annee: '',
    rt2012_re2020: false,
    accessibilite_pmr: false,
    toiture_type: '',
    toiture_materiaux: '',
    gardien: false,
    local_velos: false,
    parkings_ext: false,
    nb_parkings_ext: '',
    parkings_int: false,
    nb_parkings_int: '',
    caves: false,
    nb_caves: '',
    espaces_verts: false,
    jardins_partages: false,
    piscine: false,
    salle_sport: false,
    aire_jeux: false,
    salle_reunion: false,
    dpe_collectif: '',
    audit_energetique: false,
    audit_energetique_date: '',
    energie_utilisee: '',
    panneaux_solaires: false,
    bornes_recharge: false,
    syndicat_copro_id: '',
  });
  const [syndicats, setSyndicats] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Charge la liste des syndicats au chargement
  useEffect(() => {
    import('../services/api').then(({ default: apiClient }) => {
      apiClient.get('/syndicats_copro/')
        .then(res => setSyndicats(res.data))
        .catch(() => setSyndicats([]));
    });
  }, []);

  const handleChange = e => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSelectSyndicat = e => {
    setForm({ ...form, syndicat_copro_id: e.target.value });
  };

  const handleSubmit = e => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    import('../services/api').then(async ({ default: apiClient }) => {
      try {
        // Si syndicat non sélectionné, envoie null
        // Nettoie le payload pour n'envoyer que les champs non vides
        const payload = {};
        Object.entries(form).forEach(([key, value]) => {
          if (
            value !== '' &&
            value !== undefined &&
            !(typeof value === 'boolean' && value === false)
          ) {
            // Conversion des types
            if ([
              'annee_construction','nb_batiments','nb_lots_total','nb_lots_principaux','nb_lots_secondaires','surface_totale_m2','nb_etages','nb_ascenseurs','isolation_annee','nb_parkings_ext','nb_parkings_int','nb_caves'
            ].includes(key)) {
              payload[key] = value === '' ? null : Number(value);
            } else if ([
              'ascenseur','clim_centralisee','eau_chaude_collective','rt2012_re2020','accessibilite_pmr','gardien','local_velos','parkings_ext','parkings_int','caves','espaces_verts','jardins_partages','piscine','salle_sport','aire_jeux','salle_reunion','audit_energetique','panneaux_solaires','bornes_recharge'
            ].includes(key)) {
              payload[key] = Boolean(value);
            } else {
              payload[key] = value;
            }
          }
        });
        const coproRes = await apiClient.post('/copros/', payload);
        const coproId = coproRes.data.id;
        // Si on a un buildingId, patch l'immeuble pour lier la copro
        if (buildingId) {
          // 1. Récupère le bâtiment existant
          const buildingRes = await apiClient.get(`/buildings/${buildingId}`);
          const buildingData = buildingRes.data;
          // 2. Mets à jour copro_id
          const updatedBuilding = {
            ...buildingData,
            copro_id: coproId
          };
          // 3. Retire les champs inutiles pour l'update (id, copro, etc.)
          delete updatedBuilding.id;
          delete updatedBuilding.copro;
          // 4. Envoie tout l'objet via PUT
          await apiClient.put(`/buildings/${buildingId}`, updatedBuilding);
          // Redirige bien vers la page de l'immeuble (pas copro)
          navigate(`/buildings/${buildingId}`);
        } else {
          navigate(`/copros/${coproId}`);
        }
      } catch (err) {
        setError("Erreur lors de la création");
      } finally {
        setLoading(false);
      }
    });
  };

  return (
    <div style={{ maxWidth: 600, margin: '0 auto', padding: 32 }}>
      <button onClick={() => navigate(-1)} style={{marginBottom: 24, background: '#eee', border: 'none', borderRadius: 4, padding: '8px 18px', cursor: 'pointer', fontWeight: 'bold'}}>← Retour</button>
      <h2>Créer une copropriété</h2>
      <form onSubmit={handleSubmit}>
        <div style={{marginBottom:16}}>
          <label>Nom : <input name="nom" value={form.nom} onChange={handleChange} required /></label>
        </div>
        <div style={{marginBottom:16}}>
          <label>Rue : <input name="adresse_rue" value={form.adresse_rue} onChange={handleChange} required /></label>
        </div>
        <div style={{marginBottom:16}}>
          <label>Code postal : <input name="adresse_code_postal" value={form.adresse_code_postal} onChange={handleChange} required /></label>
        </div>
        <div style={{marginBottom:16}}>
          <label>Ville : <input name="adresse_ville" value={form.adresse_ville} onChange={handleChange} required /></label>
        </div>
        <div style={{marginBottom:16}}>
          <label>Année construction : <input name="annee_construction" type="number" value={form.annee_construction} onChange={handleChange} /></label>
        </div>
        <div style={{marginBottom:16}}>
          <label>Nombre de bâtiments : <input name="nb_batiments" type="number" value={form.nb_batiments} onChange={handleChange} /></label>
        </div>
        <div style={{marginBottom:16}}>
          <label>Nombre de lots total : <input name="nb_lots_total" type="number" value={form.nb_lots_total} onChange={handleChange} /></label>
        </div>
        <div style={{marginBottom:16}}>
          <label>Nombre de lots principaux : <input name="nb_lots_principaux" type="number" value={form.nb_lots_principaux} onChange={handleChange} /></label>
        </div>
        <div style={{marginBottom:16}}>
          <label>Nombre de lots secondaires : <input name="nb_lots_secondaires" type="number" value={form.nb_lots_secondaires} onChange={handleChange} /></label>
        </div>
        <div style={{marginBottom:16}}>
          <label>Surface totale (m²) : <input name="surface_totale_m2" type="number" step="0.01" value={form.surface_totale_m2} onChange={handleChange} /></label>
        </div>
        <div style={{marginBottom:16}}>
          <label>Type de construction : <input name="type_construction" value={form.type_construction} onChange={handleChange} /></label>
        </div>
        <div style={{marginBottom:16}}>
          <label>Nombre d'étages : <input name="nb_etages" type="number" value={form.nb_etages} onChange={handleChange} /></label>
        </div>
        <div style={{marginBottom:16}}>
          <label>Ascenseur : <input name="ascenseur" type="checkbox" checked={form.ascenseur} onChange={e=>setForm(f=>({...f,ascenseur:e.target.checked}))} /></label>
        </div>
        <div style={{marginBottom:16}}>
          <label>Nombre d'ascenseurs : <input name="nb_ascenseurs" type="number" value={form.nb_ascenseurs} onChange={handleChange} /></label>
        </div>
        <div style={{marginBottom:16}}>
          <label>Chauffage collectif (type) : <input name="chauffage_collectif_type" value={form.chauffage_collectif_type} onChange={handleChange} /></label>
        </div>
        <div style={{marginBottom:16}}>
          <label>Chauffage individuel (type) : <input name="chauffage_individuel_type" value={form.chauffage_individuel_type} onChange={handleChange} /></label>
        </div>
        <div style={{marginBottom:16}}>
          <label>Climatisation centralisée : <input name="clim_centralisee" type="checkbox" checked={form.clim_centralisee} onChange={e=>setForm(f=>({...f,clim_centralisee:e.target.checked}))} /></label>
        </div>
        <div style={{marginBottom:16}}>
          <label>Eau chaude collective : <input name="eau_chaude_collective" type="checkbox" checked={form.eau_chaude_collective} onChange={e=>setForm(f=>({...f,eau_chaude_collective:e.target.checked}))} /></label>
        </div>
        <div style={{marginBottom:16}}>
          <label>Isolation thermique : <input name="isolation_thermique" value={form.isolation_thermique} onChange={handleChange} /></label>
        </div>
        <div style={{marginBottom:16}}>
          <label>Année isolation : <input name="isolation_annee" type="number" value={form.isolation_annee} onChange={handleChange} /></label>
        </div>
        <div style={{marginBottom:16}}>
          <label>RT2012/RE2020 : <input name="rt2012_re2020" type="checkbox" checked={form.rt2012_re2020} onChange={e=>setForm(f=>({...f,rt2012_re2020:e.target.checked}))} /></label>
        </div>
        <div style={{marginBottom:16}}>
          <label>Accessibilité PMR : <input name="accessibilite_pmr" type="checkbox" checked={form.accessibilite_pmr} onChange={e=>setForm(f=>({...f,accessibilite_pmr:e.target.checked}))} /></label>
        </div>
        <div style={{marginBottom:16}}>
          <label>Type de toiture : <input name="toiture_type" value={form.toiture_type} onChange={handleChange} /></label>
        </div>
        <div style={{marginBottom:16}}>
          <label>Matériaux toiture : <input name="toiture_materiaux" value={form.toiture_materiaux} onChange={handleChange} /></label>
        </div>
        <div style={{marginBottom:16}}>
          <label>Gardien : <input name="gardien" type="checkbox" checked={form.gardien} onChange={e=>setForm(f=>({...f,gardien:e.target.checked}))} /></label>
        </div>
        <div style={{marginBottom:16}}>
          <label>Local vélos : <input name="local_velos" type="checkbox" checked={form.local_velos} onChange={e=>setForm(f=>({...f,local_velos:e.target.checked}))} /></label>
        </div>
        <div style={{marginBottom:16}}>
          <label>Parkings extérieurs : <input name="parkings_ext" type="checkbox" checked={form.parkings_ext} onChange={e=>setForm(f=>({...f,parkings_ext:e.target.checked}))} /></label>
        </div>
        <div style={{marginBottom:16}}>
          <label>Nombre parkings ext. : <input name="nb_parkings_ext" type="number" value={form.nb_parkings_ext} onChange={handleChange} /></label>
        </div>
        <div style={{marginBottom:16}}>
          <label>Parkings intérieurs : <input name="parkings_int" type="checkbox" checked={form.parkings_int} onChange={e=>setForm(f=>({...f,parkings_int:e.target.checked}))} /></label>
        </div>
        <div style={{marginBottom:16}}>
          <label>Nombre parkings int. : <input name="nb_parkings_int" type="number" value={form.nb_parkings_int} onChange={handleChange} /></label>
        </div>
        <div style={{marginBottom:16}}>
          <label>Caves : <input name="caves" type="checkbox" checked={form.caves} onChange={e=>setForm(f=>({...f,caves:e.target.checked}))} /></label>
        </div>
        <div style={{marginBottom:16}}>
          <label>Nombre de caves : <input name="nb_caves" type="number" value={form.nb_caves} onChange={handleChange} /></label>
        </div>
        <div style={{marginBottom:16}}>
          <label>Espaces verts : <input name="espaces_verts" type="checkbox" checked={form.espaces_verts} onChange={e=>setForm(f=>({...f,espaces_verts:e.target.checked}))} /></label>
        </div>
        <div style={{marginBottom:16}}>
          <label>Jardins partagés : <input name="jardins_partages" type="checkbox" checked={form.jardins_partages} onChange={e=>setForm(f=>({...f,jardins_partages:e.target.checked}))} /></label>
        </div>
        <div style={{marginBottom:16}}>
          <label>Piscine : <input name="piscine" type="checkbox" checked={form.piscine} onChange={e=>setForm(f=>({...f,piscine:e.target.checked}))} /></label>
        </div>
        <div style={{marginBottom:16}}>
          <label>Salle de sport : <input name="salle_sport" type="checkbox" checked={form.salle_sport} onChange={e=>setForm(f=>({...f,salle_sport:e.target.checked}))} /></label>
        </div>
        <div style={{marginBottom:16}}>
          <label>Aire de jeux : <input name="aire_jeux" type="checkbox" checked={form.aire_jeux} onChange={e=>setForm(f=>({...f,aire_jeux:e.target.checked}))} /></label>
        </div>
        <div style={{marginBottom:16}}>
          <label>Salle de réunion : <input name="salle_reunion" type="checkbox" checked={form.salle_reunion} onChange={e=>setForm(f=>({...f,salle_reunion:e.target.checked}))} /></label>
        </div>
        <div style={{marginBottom:16}}>
          <label>DPE collectif : <input name="dpe_collectif" value={form.dpe_collectif} onChange={handleChange} placeholder="A-G" maxLength={1} style={{width:40}} /></label>
        </div>
        <div style={{marginBottom:16}}>
          <label>Audit énergétique : <input name="audit_energetique" type="checkbox" checked={form.audit_energetique} onChange={e=>setForm(f=>({...f,audit_energetique:e.target.checked}))} /></label>
        </div>
        <div style={{marginBottom:16}}>
          <label>Date audit énergétique : <input name="audit_energetique_date" type="text" value={form.audit_energetique_date} onChange={handleChange} placeholder="YYYY-MM-DD" /></label>
        </div>
        <div style={{marginBottom:16}}>
          <label>Énergie utilisée : <input name="energie_utilisee" value={form.energie_utilisee} onChange={handleChange} /></label>
        </div>
        <div style={{marginBottom:16}}>
          <label>Panneaux solaires : <input name="panneaux_solaires" type="checkbox" checked={form.panneaux_solaires} onChange={e=>setForm(f=>({...f,panneaux_solaires:e.target.checked}))} /></label>
        </div>
        <div style={{marginBottom:16}}>
          <label>Bornes de recharge : <input name="bornes_recharge" type="checkbox" checked={form.bornes_recharge} onChange={e=>setForm(f=>({...f,bornes_recharge:e.target.checked}))} /></label>
        </div>
        <div style={{marginBottom:16}}>
          <label>Syndicat de copropriété :
            <select name="syndicat_copro_id" value={form.syndicat_copro_id} onChange={handleSelectSyndicat} style={{marginLeft:8}}>
              <option value="">Aucun</option>
              {syndicats.map(s => (
                <option key={s.id} value={s.id}>{s.nom || `Syndicat #${s.id}`}</option>
              ))}
            </select>
          </label>
        </div>
        <button type="submit" disabled={loading} style={{background:'#1976d2',color:'white',padding:'8px 18px',border:'none',borderRadius:4,cursor:'pointer',fontWeight:'bold'}}>Créer</button>
        {error && <div style={{color:'red',marginTop:8}}>{error}</div>}
      </form>
    </div>
  );
}
