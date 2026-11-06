# Déploiement Progressif et Plan de Reprise d'Activité (PRA / PCA)

Conforme à `NOTELY_plan_amelioration_complet.md` (§9.4).

---

## 1. Déploiement Progressif (Zero-Downtime)

### 1.1 Stratégie Blue/Green & Rolling

Pour garantir une disponibilité continue de l'API Notely lors des mises à jour :
1. **Conteneurisation immuable** :
   Chaque commit tagué sur `main` génère une image Docker étiquetée par son SHA git (`notely-api:sha-xxxx`).
2. **Phase d'expansion de base de données (Expand-Contract)** :
   - Les migrations Alembic sont strictement additives (`expand-only`, nouvelles colonnes `nullable=True` ou avec défaut).
   - Les instructions `DROP COLUMN` ou suppressions de tables ne sont jamais exécutées lors du déploiement applicatif initial.
3. **Bascule de trafic** :
   Le reverse proxy (Caddy / Nginx / Traefik) achemine progressivement les requêtes du cluster Blue (version actuelle) vers le cluster Green (nouvelle version) après vérification réussie de la sonde `GET /api/v1/health`.

### 1.2 Contrôle de version minimale du client (`X-Min-Client-Version`)

- Le middleware HTTP inspecte l'en-tête `X-Client-Version` envoyé par les applications Flutter et Angular.
- Si la version cliente est inférieure à `MIN_CLIENT_VERSION` (configurée dans `Settings`, ex: `1.0.0`), l'API répond immédiatement avec le code **HTTP 426 Upgrade Required**.
- L'en-tête de réponse `X-Min-Client-Version` est retourné sur chaque requête pour permettre aux clients mobiles de planifier les mises à jour préventives.

---

## 2. Plan de Reprise d'Activité (PRA / DRP)

### 2.1 Objectifs de continuité

| Indicateur | Cible Notely | Moyen mis en œuvre |
| :--- | :---: | :--- |
| **RPO** (Perte maximale de données admise) | **≤ 24 heures** | Sauvegarde quotidienne automatisée PostgreSQL (`pg_dump` chiffré) + archivage des WAL. |
| **RTO** (Délai maximal d'interruption admissible) | **≤ 4 heures** | Procédure de restauration conteneurisée reproductible et infrastructure provisionnée par Docker Compose. |

### 2.2 Procédure de sauvegarde quotidienne (RPO ≤ 24h)

Un script cron ou conteneur dédié de sauvegarde s'exécute chaque nuit à 02:00 UTC :
```bash
# Sauvegarde chiffrée avec rotation sur 30 jours
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="/backups/notely_db_${TIMESTAMP}.sql.gz"

pg_dump -h db -U notely -d notely | gzip -9 > "${BACKUP_FILE}"
# Chiffrement asymétrique ou transfert vers stockage objet immuable (S3 / GCS)
```

### 2.3 Procédure de restauration d'urgence (RTO ≤ 4h)

En cas de sinistre d'infrastructure ou de corruption majeure :
1. **Provisionnement des conteneurs** :
   ```bash
   docker compose down -v
   docker compose up -d db redis
   ```
2. **Restauration de la dernière sauvegarde saine** :
   ```bash
   gunzip -c /backups/notely_db_LAST_SAFE.sql.gz | psql -h localhost -U notely -d notely
   ```
3. **Exécution des migrations résiduelles** :
   ```bash
   docker compose run --rm api alembic upgrade head
   ```
4. **Vérification de cohérence** :
   ```bash
   docker compose run --rm api alembic check
   curl -f http://localhost:8000/api/v1/health
   ```
5. **Redémarrage des workers Celery et de l'API** :
   ```bash
   docker compose up -d api celery_worker
   ```

### 2.4 Procédure de Rollback de Modèle IA (en 1 commande)

Si une nouvelle version de modèle HTR introduit des dérives ou régressions en production (§8.7 #4) :
```bash
# Rollback immédiat vers la version précédente sans redémarrer le serveur
python -m training.promote --rollback trocr_fr
```
Le registre de moteurs recharge à chaud le modèle précédent en moins de 60 secondes.
