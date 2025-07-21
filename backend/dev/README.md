# Dossier de Développement

Ce dossier contient les fichiers et scripts utilisés uniquement en développement.

## Structure

- `tests/` : Scripts de test et validation
- `migrations/` : Scripts de migration de base de données
- `scripts/` : Scripts utilitaires et d'installation

## Utilisation

Ces fichiers ne doivent PAS être déployés en production.
Ils sont conservés pour le développement et la maintenance.

## Scripts de Migration

Les scripts de migration doivent être exécutés dans l'ordre chronologique.
Vérifiez toujours l'état de la base avant d'exécuter une migration.

## Scripts de Test

Utilisez les scripts de test pour valider les fonctionnalités avant déploiement.
