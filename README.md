# TDA-MAC

## Description
TDA-MAC est un protocole conçu pour les réseaux de communication acoustique sous-marine. Ce projet vise à implémenter et tester ce protocole sur un modem acoustique Ahoi, en optimisant la transmission des données tout en minimisant les pertes de paquets et les interférences.

## Prérequis

### 1.) Installation de Python
TDA-MAC fonctionne avec Python 3.x. Il est recommandé d'utiliser la dernière version disponible. Assurez-vous également d'avoir `pip` installé pour gérer les dépendances du projet.

### 2.) Dépendances Python
Les bibliothèques nécessaires sont listées dans le fichier `requirements.txt`. L'installation doit se faire dans un environnement virtuel pour éviter les conflits de dépendances.

```sh
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

### 3.) Installation de PyLib
Après l'installation des dépendances, ajoutez la bibliothèque locale PyLib :

```sh
pip install -e .
```

Ajoutez ensuite le chemin de la bibliothèque à votre environnement :

```sh
export PYTHONPATH=${PYTHONPATH}:/path/to/lib/
```

## Utilisation

1. **Configuration** : Assurez-vous que les modems Ahoi sont connectés et configurés correctement(transducteur, puissance, ..).
2. **Lancement** : Exécutez les script dans working_stage pour démarrer la communication en utilisant le protocole TDA-MAC.
3. **Tests** : Des tests en laboratoire et en conditions réelles peuvent être réalisés pour évaluer les performances du protocole.

## Auteurs
- Théo Lebail
- Thomas Lebreton

Encadré par :
- Benoit Parrein
- Cyprien Aoustin

---

Ce projet a été développé dans le cadre d'un travail de recherche à l'École Polytechnique de l'Université de Nantes.
