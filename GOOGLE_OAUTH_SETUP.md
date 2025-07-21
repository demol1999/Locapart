# Configuration Google OAuth - Guide complet

## Étape 1: Créer un projet Google Cloud

1. Allez sur [Google Cloud Console](https://console.cloud.google.com/)
2. Créez un nouveau projet ou sélectionnez un projet existant
3. Notez le nom du projet

## Étape 2: APIs (Optionnel)

Cette étape peut être ignorée pour un test simple. Les APIs OAuth de base sont déjà activées par défaut.

Si vous avez des problèmes plus tard, vous pourrez activer :
1. Dans **API & Services** > **Library**
2. Recherchez "Google Identity" et activez les APIs si nécessaire

## Étape 3: Configurer l'écran de consentement OAuth

1. Allez dans **API & Services** > **OAuth consent screen**
2. Choisissez **External** (pour tester avec votre compte Google personnel)
3. Remplissez les informations obligatoires :
   - **App name**: Locapart (ou le nom de votre choix)
   - **User support email**: votre email
   - **Developer contact email**: votre email
4. Cliquez **Save and Continue**
5. **Scopes** : Pour une application de test, vous pouvez **ignorer cette étape** en cliquant **Save and Continue**
   - Les scopes de base (email, profile, openid) sont automatiquement inclus
   - Si vous voulez être précis, cliquez "Add or Remove Scopes" et cherchez :
     - `../auth/userinfo.email`
     - `../auth/userinfo.profile` 
     - `openid`
6. Dans **Test users**, ajoutez votre email Google pour pouvoir tester
7. Cliquez **Save and Continue** jusqu'à la fin

## Étape 4: Créer les identifiants OAuth

1. Allez dans **API & Services** > **Credentials**
2. Cliquez **+ CREATE CREDENTIALS** > **OAuth 2.0 Client IDs**
3. Choisissez **Web application**
4. Donnez un nom : "Locapart Development"
5. Dans **Authorized redirect URIs**, ajoutez TOUTES ces URLs :
   ```
   http://localhost:8000/auth/google/callback
   http://127.0.0.1:8000/auth/google/callback
   http://localhost:5173/auth/google/callback
   http://127.0.0.1:5173/auth/google/callback
   ```
6. Cliquez **Create**

## Étape 5: Récupérer les identifiants

1. Une popup apparaît avec :
   - **Client ID** : commence par quelque chose comme `123456789-abc.apps.googleusercontent.com`
   - **Client Secret** : une chaîne aléatoire
2. **COPIEZ CES VALEURS** - vous en aurez besoin !

## Étape 6: Configurer les variables d'environnement

1. Dans le dossier `backend/`, créez ou modifiez le fichier `.env`
2. Ajoutez ces lignes avec VOS valeurs :

```env
# Configuration OAuth Google
GOOGLE_CLIENT_ID=votre_client_id_ici.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=votre_client_secret_ici

# Autres configurations OAuth (optionnel pour l'instant)
FACEBOOK_CLIENT_ID=your_facebook_app_id_here
FACEBOOK_CLIENT_SECRET=your_facebook_app_secret_here
MICROSOFT_CLIENT_ID=your_microsoft_app_id_here
MICROSOFT_CLIENT_SECRET=your_microsoft_app_secret_here
MICROSOFT_TENANT_ID=common
```

## Étape 7: Tester la configuration

1. Redémarrez le serveur backend
2. Lancez le diagnostic :
   ```bash
   cd backend
   python diagnose_oauth.py
   ```
3. Vérifiez que Google affiche maintenant "OK" avec vos identifiants

## Étape 8: Test complet

1. Allez sur http://localhost:5173/login
2. Cliquez sur "Continuer avec Google"
3. Vous devriez être redirigé vers Google pour autoriser l'accès
4. Après autorisation, vous devriez être connecté automatiquement

## Dépannage

### Erreur "Accès bloqué : erreur d'autorisation"
- Vérifiez que votre email est dans les "Test users" de l'écran de consentement
- Vérifiez que les URLs de redirection sont exactement correctes
- Vérifiez que les variables d'environnement sont bien chargées

### Erreur "redirect_uri_mismatch"
- L'URL de redirection dans Google Console doit EXACTEMENT correspondre
- Vérifiez http vs https
- Vérifiez localhost vs 127.0.0.1
- Vérifiez le port (8000 pour le backend, 5173 pour le frontend)

### Variables d'environnement non chargées
- Vérifiez que le fichier `.env` est dans le bon dossier (`backend/`)
- Redémarrez complètement le serveur backend
- Utilisez `python -c "import os; print(os.getenv('GOOGLE_CLIENT_ID'))"` pour vérifier