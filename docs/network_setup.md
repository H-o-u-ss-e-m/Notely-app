# Guide de Configuration Réseau Local (PC ↔ Téléphone Mobile)

## 1. Démarrer le Backend sur le PC
Le backend est configuré pour écouter sur `0.0.0.0:8000` (toutes les cartes réseau).

```bash
cd backend
python run_backend.py
```

## 2. Trouver l'adresse IPv4 de votre PC sur le Wi-Fi
Dans l'invite de commande (CMD) ou PowerShell sur votre PC :
```bash
ipconfig
```
Repérez la ligne **Adresse IPv4** sous la carte Wi-Fi (ex: `192.168.1.50`).

## 3. Connecter votre Téléphone Android
1. Connectez votre téléphone au **même réseau Wi-Fi** que votre PC.
2. Dans le code Flutter `mobile/lib/core/config/env_config.dart`, modifiez la variable :
   ```dart
   static String baseUrl = "http://192.168.1.50:8000/api/v1";
   ```
3. Lancez l'application Flutter sur votre téléphone (`flutter run`).
4. L'application mobile envoie les strokes au PC et reçoit la transcription TrOCR en direct !
