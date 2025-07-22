# 🔄 Système d'Audit Avancé avec Undo - LocAppart

## 🎯 Vue d'ensemble

Un système complet d'audit et d'annulation (undo) a été implémenté pour permettre aux administrateurs de voir toutes les actions des utilisateurs sur les 7 derniers jours et d'annuler certaines actions si nécessaire.

## ✨ Fonctionnalités Principales

### 🔍 **Timeline d'Audit Utilisateur**
- **Visualisation** : Actions groupées par transaction avec horodatage
- **Filtrage** : Par type d'action, complexité, période
- **Détails** : Impact complet de chaque action avec métadonnées
- **Permissions** : Différents niveaux selon le rôle admin

### ⏪ **Système d'Undo Intelligent**
- **3 Niveaux de Complexité** :
  - `SIMPLE` : UPDATE utilisateur (tous admins)
  - `MODERATE` : CREATE/DELETE basique (SUPPORT+)  
  - `COMPLEX` : DELETE avec dépendances (SUPER_ADMIN uniquement)
- **Vérifications Avancées** : Pré-requis, dépendances, conflits
- **Backup Complet** : Sauvegarde JSON + fichiers pour restauration

### 🔔 **Notifications Utilisateur (Cloche)**
- **Notification Automatique** : L'utilisateur est informé quand un admin undo ses actions
- **Types de Notifications** : Admin actions, undo performed, system alerts
- **API Complète** : Marquer lu, archiver, résumé pour la cloche
- **Priorités** : Normal, high, urgent avec couleurs différentes

### 💾 **Backup et Restauration**
- **Vrais Backups** : Données complètes JSON + fichiers
- **Rétention** : 7 jours configurables
- **Restauration Intelligente** : Vérification de cohérence avant restore

## 🗃️ Architecture de Base de Données

### **Nouvelles Tables Créées**

```sql
-- Audit avancé avec métadonnées complètes
audit_logs_enhanced
├── transaction_group_id (groupement d'actions)
├── before_data / after_data (JSON complet)
├── undo_complexity (SIMPLE/MODERATE/COMPLEX)
├── related_entities (entités affectées)
└── expires_at (7 jours)

-- Sauvegarde pour restauration
data_backups
├── full_backup_data (JSON complet)
├── relationships_data (relations)
├── files_backup_path (fichiers sauvés)
└── compression_used

-- Actions d'undo effectuées
undo_actions
├── status (PENDING/EXECUTING/COMPLETED/FAILED)
├── execution_log (détails d'exécution)
├── preview_data (aperçu des changements)
└── error_message (si échec)

-- Notifications utilisateur
user_notifications
├── notification_type (ADMIN_ACTION/UNDO_PERFORMED/etc.)
├── priority (normal/high/urgent)
├── is_read / read_at
├── notification_metadata (données JSON)
└── expires_at

-- Groupement de transactions
audit_transaction_groups
├── group_name ("Création immeuble avec 5 appartements")
├── complexity_level (niveau global du groupe)
├── all_undoable (si tout peut être undone)
└── has_been_undone (si déjà undone)
```

## 🛠️ APIs Disponibles

### **Routes Admin d'Audit**

```http
# Timeline d'un utilisateur (7 derniers jours)
GET /audit/users/{user_id}/timeline?days=7&include_non_undoable=true

# Pré-requis pour un undo
GET /audit/actions/{audit_log_id}/requirements

# Aperçu de l'impact d'un undo
GET /audit/actions/{audit_log_id}/preview

# Effectuer un undo (avec confirmation pour actions complexes)
POST /audit/actions/{audit_log_id}/undo
{
  "reason": "Erreur de manipulation utilisateur",
  "confirm_complex": true
}

# Historique des undo effectués
GET /audit/undo-history/{user_id}

# Recherche dans les logs d'audit
GET /audit/search?query=appartement&days=7&entity_type=APARTMENT

# Statistiques globales d'audit
GET /audit/stats/global?days=30
```

### **Routes Utilisateur de Notifications**

```http
# Résumé pour la cloche (nombre non lues, urgentes)
GET /audit/notifications/summary

# Liste des notifications
GET /audit/notifications?unread_only=false&limit=20

# Marquer comme lu
POST /audit/notifications/mark-read
{
  "notification_ids": [1, 2, 3],
  "mark_all": false
}

# Archiver des notifications
POST /audit/notifications/archive
{
  "archive_read": true,
  "older_than_days": 30
}
```

## 🎨 Interface Admin Proposée

### **Timeline Utilisateur**
```
┌─ Timeline: john@example.com (7 derniers jours) ─────────┐
│                                                          │
│ ┌─ 21/07/2025 14:30 ────────────────────────────────┐   │
│ │ 🏗️ GROUPE: "Création appartement avec photos"     │   │
│ │     ├─ CREATE Appartement "T3 Rue de la Paix"     │   │
│ │     ├─ CREATE Photo "salon.jpg"                    │   │
│ │     └─ CREATE Photo "cuisine.jpg"                  │   │
│ │     Impact: +1 appartement, +2 photos             │   │
│ │     [🔙 Undo Groupe] [👁️ Détails] [⚠️ Modéré]    │   │
│ └────────────────────────────────────────────────────┘   │
│                                                          │
│ ┌─ 21/07/2025 12:15 ────────────────────────────────┐   │
│ │ ✏️ UPDATE: "Modification profil utilisateur"       │   │
│ │     nom: "Jean Dupont" → "Jean Martin"             │   │
│ │     [🔙 Undo] [👁️ Détails] [✅ Simple]            │   │
│ └────────────────────────────────────────────────────┘   │
│                                                          │
│ ┌─ 20/07/2025 16:45 ────────────────────────────────┐   │
│ │ 🔐 LOGIN depuis 192.168.1.100                      │   │
│ │     [❌ Non-annulable] [👁️ Détails]               │   │
│ └────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────┘
```

### **Dialogue de Confirmation Undo**
```
┌─ Confirmer l'annulation ─────────────────────────────────┐
│                                                          │
│ ⚠️ Action COMPLEXE détectée                              │
│                                                          │
│ Action à annuler:                                        │
│ CREATE Appartement "T3 Rue de la Paix"                  │
│ Créé le: 21/07/2025 à 14:30                            │
│                                                          │
│ Impact de l'annulation:                                  │
│ • ❌ Suppression définitive de l'appartement             │
│ • ❌ Suppression de 2 photos associées                   │
│ • ⚠️ Suppression de 1 bail en cours                     │
│                                                          │
│ Durée estimée: 2-5 minutes                              │
│                                                          │
│ Raison (obligatoire):                                    │
│ ┌──────────────────────────────────────────────────────┐ │
│ │ Erreur de saisie - mauvaise adresse                 │ │
│ └──────────────────────────────────────────────────────┘ │
│                                                          │
│ ☐ Je comprends que cette action est irréversible        │
│                                                          │
│ [Annuler] [🔙 Confirmer l'Undo]                         │
└──────────────────────────────────────────────────────────┘
```

### **Cloche de Notifications**
```
┌─ Notifications (3 non lues) ─┐
│                               │
│ 🔴 ⚠️  Action admin           │
│   Appartement supprimé        │
│   Il y a 5 min               │
│                               │
│ 🟠 🔄 Undo effectué          │
│   Profil restauré            │
│   Il y a 1h                  │
│                               │
│ 🟢 ℹ️  Système               │
│   Quota bientôt atteint      │
│   Il y a 2h                  │
│                               │
│ [Tout marquer lu] [Voir tout] │
└───────────────────────────────┘
```

## 🔐 Sécurité et Permissions

### **Niveaux d'Accès**
- **VIEWER** : Aucun undo
- **MODERATOR** : Undo SIMPLE uniquement  
- **USER_MANAGER** : Undo SIMPLE + MODERATE
- **SUPPORT** : Undo SIMPLE + MODERATE
- **SUPER_ADMIN** : Tous les undo (y compris COMPLEX)

### **Auditing des Actions Admin**
- Chaque undo est lui-même audité
- Notification automatique à l'utilisateur affecté
- Log complet de l'exécution avec détails techniques
- Historique des actions admin consultable

### **Protections**
- Vérification de cohérence avant undo
- Détection des modifications ultérieures conflictuelles  
- Confirmation obligatoire pour actions complexes
- Backup automatique avec expiration après 7 jours

## 📊 Exemples d'Usage

### **Scénario 1: Erreur Utilisateur Simple**
```
Utilisateur modifie son nom par erreur
→ Admin voit dans timeline: UPDATE nom "Jean" → "Wrong"
→ Clic "Undo" → Confirmation simple
→ Nom restauré à "Jean"
→ Notification envoyée à l'utilisateur
```

### **Scénario 2: Suppression Accidentelle Complexe** 
```
Utilisateur supprime immeuble avec 5 appartements
→ Admin voit: DELETE Building avec related_entities: [5 apartments, 12 photos]
→ Système indique COMPLEX (backup complet disponible)
→ Seul SUPER_ADMIN peut undo
→ Confirmation obligatoire avec aperçu des impacts
→ Restauration complète depuis backup JSON
→ Notification détaillée à l'utilisateur
```

### **Scénario 3: Actions Groupées**
```
Utilisateur crée immeuble + appartements + photos en une session
→ Timeline groupe les actions par transaction_group_id
→ Admin peut undo tout le groupe d'un coup
→ Ou undo action par action selon les besoins
```

## 🚀 État d'Implémentation

### ✅ **Complété**
- [x] Architecture complète du système
- [x] Base de données avec toutes les tables
- [x] Services d'audit avancé et d'undo  
- [x] API complète avec routes admin et utilisateur
- [x] Système de notifications avec cloche
- [x] Backup et restauration intelligents
- [x] Migration de base de données
- [x] Intégration dans main.py
- [x] Gestion des permissions par rôle
- [x] Documentation complète

### 🎯 **Prochaines Étapes (Optionnelles)**
- [ ] Interface web admin pour la timeline
- [ ] Système d'email en complément des notifications  
- [ ] Paramétrage utilisateur des notifications
- [ ] Dashboard de statistiques d'undo
- [ ] Export des audits en CSV/Excel
- [ ] Système d'alertes automatiques
- [ ] Intégration avec système de monitoring

## 📝 Notes Techniques

### **Performance**
- Index optimisés pour les requêtes temporelles
- Expiration automatique des données après 7 jours
- Pagination sur toutes les listes
- Compression optionnelle des backups

### **Scalabilité**
- Partitioning possible par date sur audit_logs_enhanced
- Archivage automatique des anciens logs
- Cleanup job pour les backups expirés

### **Monitoring**
- Métriques disponibles via /audit/stats/global
- Logs d'erreur détaillés pour debugging
- Alertes système pour échecs d'undo

---

🎉 **Le système d'audit avancé avec undo est maintenant pleinement opérationnel !** 

Les administrateurs peuvent voir toutes les actions des utilisateurs sur 7 jours et annuler les actions problématiques, avec notification automatique des utilisateurs concernés. La cloche de notification permet aux utilisateurs d'être informés en temps réel des actions administratives les concernant.