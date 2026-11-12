# Preuves Partie 2 — Pipeline CI/CD : erreur → correction → vert

Pour chaque contrôle du pipeline qui échoue, trois preuves sont conservées :

1. **erreur** : le job rouge dans GitHub Actions et l'extrait du journal qui
   montre la cause ;
2. **correction** : le diff du commit qui corrige ;
3. **après** : le même job vert sur le run suivant.

Numérotation à partir de **40** (00-39 et M01-M10 sont utilisés en Partie 1).
Journaux : `logs/NN-*.txt` (commande exacte, sortie, code de retour) ;
captures : `captures/NN-*.png`. Générés avec :

```bash
CAPTURE_DIR=docs/preuves/corrvulnecicd scripts/capture_cmd.sh NN-description '<commande>'
.venv/bin/python scripts/capture_web.py <url du run> docs/preuves/corrvulnecicd/captures/NN-description.png
```

Règle : aucune valeur de secret ni jeton dans les preuves (valeurs de V3 masquées).

## Run 1 — Pipeline sur la version vulnérable (preuves « avant »)

| N° | Ce que la preuve montre | Journal | Capture |
|----|-------------------------|---------|---------|
| _à venir_ | | | |

## Corrections

| N° | Erreur | Correction | Après |
|----|--------|------------|-------|
| _à venir_ | | | |
