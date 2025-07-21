# Guide de Configuration Stripe

Ce guide détaille la configuration complète du système de paiement Stripe pour LocAppart.

## 📋 Prérequis

1. Compte Stripe (https://dashboard.stripe.com)
2. Python 3.8+ avec pip
3. Base de données MySQL/MariaDB configurée
4. Application LocAppart fonctionnelle

## 🚀 Installation

### 1. Installation des dépendances Stripe

```bash
cd backend
python install_stripe.py
```

### 2. Migration de la base de données

```bash
cd backend
python migrate_subscription_tables.py
```

## ⚙️ Configuration Stripe Dashboard

### 1. Créer un produit Premium

1. Connectez-vous au [Stripe Dashboard](https://dashboard.stripe.com)
2. Allez dans **Produits** → **Ajouter un produit**
3. Configurez le produit :
   - **Nom** : "Abonnement Premium LocAppart"
   - **Description** : "Accès illimité à toutes les fonctionnalités"
   - **Prix** : 9,99 EUR/mois
   - **Type de facturation** : Récurrent
   - **Période** : Mensuel

4. Notez l'ID du prix (commence par `price_...`)

### 2. Configurer les webhooks

1. Dans le dashboard Stripe, allez dans **Développeurs** → **Webhooks**
2. Cliquez sur **Ajouter un endpoint**
3. Configurez l'endpoint :
   - **URL** : `https://votre-domaine.com/api/stripe/webhook`
   - **Description** : "LocAppart Webhooks"
   - **Événements à écouter** :
     - `customer.subscription.created`
     - `customer.subscription.updated`
     - `customer.subscription.deleted`
     - `invoice.payment_succeeded`
     - `invoice.payment_failed`
     - `payment_intent.succeeded`
     - `payment_intent.payment_failed`

4. Notez la clé secrète du webhook (commence par `whsec_...`)

### 3. Récupérer les clés API

1. Dans **Développeurs** → **Clés API**, récupérez :
   - **Clé publique** (commence par `pk_test_...` ou `pk_live_...`)
   - **Clé secrète** (commence par `sk_test_...` ou `sk_live_...`)

## 🔧 Configuration des variables d'environnement

Ajoutez ces variables à votre fichier `.env` :

```env
# Configuration Stripe
STRIPE_SECRET_KEY=sk_test_votre_cle_secrete_ici
STRIPE_PUBLISHABLE_KEY=pk_test_votre_cle_publique_ici
STRIPE_WEBHOOK_SECRET=whsec_votre_secret_webhook_ici
STRIPE_PREMIUM_PRICE_ID=price_votre_id_prix_premium_ici
```

## 🧪 Test de l'installation

### 1. Démarrer l'application

```bash
# Backend
cd backend
uvicorn main:app --reload

# Frontend
cd frontend
npm run dev
```

### 2. Tests manuels

1. **Créer un compte utilisateur** ou se connecter
2. **Accéder à la page d'abonnement** : `/subscription`
3. **Vérifier les limites** : Essayer d'ajouter plus de 3 appartements
4. **Tester le paiement** : Cliquer sur "Passer au Premium"
5. **Utiliser une carte de test Stripe** :
   - Numéro : `4242 4242 4242 4242`
   - Date : `12/25`
   - CVC : `123`

### 3. Vérification des webhooks

1. Dans le dashboard Stripe, allez dans **Développeurs** → **Webhooks**
2. Cliquez sur votre endpoint
3. Vérifiez que les événements arrivent correctement

## 📊 Fonctionnalités implémentées

### ✅ Backend

- **Modèles de données** : `UserSubscription`, `Payment`
- **Service Stripe** : Gestion des clients, abonnements, webhooks
- **Middleware de limite** : Vérification automatique des limites d'appartements
- **API Routes** :
  - `GET /api/stripe/subscription` - Abonnement utilisateur
  - `GET /api/stripe/apartment-limit` - Vérification des limites
  - `POST /api/stripe/create-checkout-session` - Création session de paiement
  - `POST /api/stripe/cancel-subscription` - Annulation abonnement
  - `GET /api/stripe/payments` - Historique des paiements
  - `POST /api/stripe/webhook` - Webhooks Stripe
  - `GET /api/stripe/publishable-key` - Clé publique pour le frontend

### ✅ Frontend

- **Page d'abonnement** : `/subscription`
- **Historique des paiements** : `/payments`
- **Navigation** : Liens dans la navbar
- **Gestion des erreurs** : Messages d'erreur utilisateur-friendly
- **Interface responsive** : Mobile et desktop

### ✅ Logique métier

- **Abonnement gratuit** : 3 appartements maximum
- **Abonnement premium** : Appartements illimités
- **Vérification automatique** : Middleware sur la création d'appartements
- **Audit complet** : Logs de toutes les actions Stripe

## 🔒 Sécurité

### Bonnes pratiques implémentées

1. **Validation des webhooks** : Vérification de signature Stripe
2. **Clés d'environnement** : Jamais de clés en dur dans le code
3. **Audit logging** : Traçabilité de toutes les actions
4. **Gestion d'erreurs** : Pas d'exposition d'informations sensibles
5. **Validation des données** : Schémas Pydantic pour toutes les entrées

## 🚨 Dépannage

### Problèmes courants

#### 1. Erreur "Stripe key not found"
- Vérifiez que les variables d'environnement sont correctement définies
- Redémarrez l'application après modification du `.env`

#### 2. Webhooks non reçus
- Vérifiez l'URL du webhook dans le dashboard Stripe
- Assurez-vous que l'endpoint est accessible publiquement
- Vérifiez les logs du webhook dans Stripe

#### 3. Erreur de limite d'appartements
- Vérifiez l'abonnement de l'utilisateur : `GET /api/stripe/subscription`
- Vérifiez les logs d'audit dans la base de données

#### 4. Paiement échoué
- Utilisez les cartes de test Stripe appropriées
- Vérifiez les logs dans le dashboard Stripe
- Consultez l'historique des paiements : `GET /api/stripe/payments`

### Logs utiles

```bash
# Vérifier les abonnements en base
mysql -u maria_user -p locappart_db
SELECT * FROM user_subscriptions;

# Vérifier les paiements
SELECT * FROM payments ORDER BY created_at DESC LIMIT 10;

# Vérifier les logs d'audit
SELECT * FROM audit_logs WHERE entity_type IN ('SUBSCRIPTION', 'PAYMENT') ORDER BY created_at DESC LIMIT 20;
```

## 📈 Monitoring et métriques

### Endpoints de statistiques

```http
GET /api/stripe/stats
```

Retourne :
- Nombre total d'utilisateurs
- Répartition Free/Premium
- Abonnements actifs/annulés
- Revenu mensuel

### Métriques à surveiller

1. **Taux de conversion** : Free → Premium
2. **Churn rate** : Annulations d'abonnements
3. **Revenus mensuels récurrents** (MRR)
4. **Échecs de paiement**

## 🔄 Migration vers la production

### 1. Passer en mode live Stripe

1. Activez votre compte Stripe live
2. Remplacez les clés de test par les clés live
3. Recréez les webhooks avec l'URL de production
4. Mettez à jour `STRIPE_PREMIUM_PRICE_ID` avec l'ID live

### 2. Variables d'environnement production

```env
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PREMIUM_PRICE_ID=price_...
```

### 3. Tests en production

1. Effectuez des tests avec de vraies cartes (petits montants)
2. Vérifiez les webhooks en production
3. Testez les annulations et remboursements

## 📞 Support

En cas de problème :

1. **Logs d'application** : Consultez les logs FastAPI
2. **Dashboard Stripe** : Vérifiez les événements et erreurs
3. **Base de données** : Consultez les tables `audit_logs`, `user_subscriptions`, `payments`
4. **Documentation Stripe** : https://stripe.com/docs

---

✅ **Système de paiement Stripe complètement intégré et fonctionnel !**