# Configuration du Système de Vérification Email

## Vue d'ensemble

Le système de vérification email a été implémenté avec une architecture SOLID supportant plusieurs providers d'emails. Les utilisateurs qui s'inscrivent avec email/password recevront automatiquement un email de vérification.

## Providers Email Supportés

### 1. Resend (Recommandé)
- **Prix**: Gratuit jusqu'à 3000 emails/mois
- **Avantages**: Simple, rapide, interface moderne
- **Site**: https://resend.com/

### 2. Mailgun
- **Prix**: Gratuit jusqu'à 5000 emails/mois
- **Avantages**: Très fiable, analytics détaillées
- **Site**: https://www.mailgun.com/

### 3. SMTP
- **Prix**: Dépend de votre fournisseur
- **Avantages**: Compatible avec tout serveur SMTP
- **Usage**: Pour serveurs email internes ou autres providers

## Configuration

### Étape 1: Choisir un Provider

#### Option A: Resend (Recommandé)
1. Créer un compte sur https://resend.com/
2. Aller dans "API Keys" et créer une nouvelle clé
3. Ajouter à votre `.env`:
```bash
RESEND_API_KEY=re_your_api_key_here
EMAIL_PROVIDER=resend
EMAIL_FROM=noreply@votre-domaine.com
EMAIL_FROM_NAME=VotreApp
```

#### Option B: Mailgun
1. Créer un compte sur https://www.mailgun.com/
2. Configurer un domaine ou utiliser le sandbox
3. Récupérer l'API Key et le domaine
4. Ajouter à votre `.env`:
```bash
MAILGUN_API_KEY=your_mailgun_api_key
MAILGUN_DOMAIN=your_domain.mailgun.org
EMAIL_PROVIDER=mailgun
EMAIL_FROM=noreply@votre-domaine.com
EMAIL_FROM_NAME=VotreApp
```

#### Option C: SMTP
1. Configurer votre serveur SMTP
2. Ajouter à votre `.env`:
```bash
SMTP_HOST=smtp.your-provider.com
SMTP_PORT=587
SMTP_USERNAME=your_username
SMTP_PASSWORD=your_password
SMTP_TLS=true
EMAIL_PROVIDER=smtp
EMAIL_FROM=noreply@votre-domaine.com
EMAIL_FROM_NAME=VotreApp
```

### Étape 2: Redémarrer l'Application
```bash
cd backend
uvicorn main:app --reload
```

## Fonctionnalités

### Inscription Automatique
- Les utilisateurs email/password reçoivent automatiquement un email de vérification
- Les utilisateurs OAuth (Google, Facebook, Microsoft) sont automatiquement vérifiés

### API Endpoints
- `POST /api/email-verification/send` - Envoyer un code de vérification
- `POST /api/email-verification/verify-code` - Vérifier un code à 6 chiffres
- `POST /api/email-verification/verify-token` - Vérifier via URL
- `GET /api/email-verification/status` - Statut de vérification
- `POST /api/email-verification/resend` - Renvoyer l'email

### Sécurité
- Rate limiting sur les endpoints
- Codes expirables (15 minutes)
- Audit logging complet
- Protection contre les attaques par force brute

### Middleware de Protection
```python
from email_verification_middleware import require_verified_email

@app.get("/protected-endpoint")
def protected_action(user = Depends(require_verified_email)):
    # Cette action nécessite un email vérifié
    pass
```

## Tester le Système

### Test Base de Données
```bash
cd backend
python test_email_verification_complete.py
```

### Test API
1. Créer un nouvel utilisateur via `/signup/`
2. Vérifier que l'email est envoyé
3. Utiliser le code reçu avec `/api/email-verification/verify-code`

## Templates Email

Les emails contiennent:
- Code de vérification à 6 chiffres
- Lien de vérification direct
- Instructions claires
- Design responsive

## Troubleshooting

### "RESEND_API_KEY manquante"
- Vérifier que la variable est dans `.env`
- Redémarrer l'application

### "Email non envoyé"
- Vérifier les logs d'audit
- Tester la connectivité du provider
- Vérifier les limites de quota

### "Code invalide"
- Le code expire après 15 minutes
- Utiliser `/resend` pour un nouveau code
- Vérifier la casse (codes en majuscules)

## Architecture

Le système suit les principes SOLID:
- **S**ingle Responsibility: Chaque provider gère un type d'email
- **O**pen/Closed: Facile d'ajouter de nouveaux providers
- **L**iskov Substitution: Tous les providers sont interchangeables
- **I**nterface Segregation: Interface simple et focalisée
- **D**ependency Inversion: Le service dépend d'interfaces, pas d'implémentations

## Migration

La migration a été automatiquement exécutée. Si vous devez la relancer:
```bash
cd backend
python migrate_email_verification.py
```