import os
import json
import re
import time
from typing import Dict, Any
import urllib.request
import urllib.error

try:
    from django.conf import settings
except Exception:
    settings = None

# Google Gemini
# Clé chargée depuis l'environnement ou les settings Django (pas de clé en dur)
GEMINI_API_KEY = (
    os.getenv("GEMINI_API_KEY")
    or (getattr(settings, "GEMINI_API_KEY", "") if settings else "")
)
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-pro-latest")
GEMINI_API_URL_BASE = "https://generativelanguage.googleapis.com/v1beta/models/"


def _extract_json(text: str) -> Dict[str, Any]:
    if not text:
        return {}
    cleaned = re.sub(r'```json\s*|\s*```', '', text.strip())
    try:
        return json.loads(cleaned)
    except:
        pass
    start = cleaned.find('{')
    end = cleaned.rfind('}')
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(cleaned[start:end+1])
        except:
            pass
    return {}


def _build_prompt(entry) -> str:
    mood = getattr(entry, 'get_mood_display', lambda: '')() or 'Non spécifié'
    energy = getattr(entry, 'energy_level', 'Non spécifié')
    sleep = getattr(entry, 'sleep_quality', 'Non spécifié')
    main_subject = getattr(entry, 'main_subject', '') or 'Général'
    content = getattr(entry, 'content', '') or ''
    return f"""Analyse cette entrée de journal et recommande 2-3 activités pratiques.

CONTEXTE:
- Humeur: {mood}
- Énergie: {energy}/5  
- Sommeil: {sleep}/5
- Sujet: {main_subject}
- Résumé: {content[:200]}

Génère UNIQUEMENT du JSON avec ce format exact:

{{
  "activities": [
    {{
      "label": "Nom de l'activité",
      "category": "sport|detente|creativite|social",
      "why": "Pourquoi cette activité est pertinente",
      "duration_min": 15
    }}
  ]
}}

Sois concret et bienveillant. Réponds uniquement avec le JSON valide."""


def recommend_activities_gemini(entry, max_retries: int = 2) -> Dict[str, Any]:
    key = GEMINI_API_KEY.strip()
    if not key:
        return {"activities": [], "error": "Clé API Gemini manquante"}
    primary = GEMINI_MODEL.strip()

    def _pick_available_model() -> str:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
            req = urllib.request.Request(url, headers={"Accept": "application/json"}, method="GET")
            with urllib.request.urlopen(req, timeout=30) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            models = payload.get("models", [])
            supported = [
                m["name"].split("/", 1)[1]
                for m in models
                if "generateContent" in m.get("supportedGenerationMethods", [])
            ]
            preferred_order = [
                "gemini-pro-latest",
                "gemini-flash-latest",
                "gemini-2.5-flash-lite",
                "gemma-3-27b-it",
                "gemma-3-12b-it"
            ]
            for pref in preferred_order:
                if pref in supported:
                    return pref
            return supported[0] if supported else ""
        except Exception:
            return ""

    autodetected = _pick_available_model()
    models_to_try = []
    if autodetected and autodetected not in models_to_try:
        models_to_try.append(autodetected)
    if primary not in models_to_try:
        models_to_try.append(primary)
    for fb in [
        "gemini-pro-latest",
        "gemini-flash-latest",
        "gemini-2.5-flash-lite",
        "gemma-3-27b-it",
        "gemma-3-12b-it"
    ]:
        if fb not in models_to_try:
            models_to_try.append(fb)

    prompt = _build_prompt(entry)
    headers = {"Content-Type": "application/json"}

    for attempt in range(max_retries):
        for mdl in models_to_try:
            try:
                print(f"🔍 Tentative avec le modèle: {mdl}")
                endpoint = f"{GEMINI_API_URL_BASE}{mdl}:generateContent?key={key}"
                body_obj = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.2,
                        "maxOutputTokens": 450,
                        "topP": 0.9,
                        "responseMimeType": "application/json"
                    }
                }
                body = json.dumps(body_obj).encode("utf-8")
                req = urllib.request.Request(endpoint, data=body, headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=90) as resp:
                    resp_text = resp.read().decode("utf-8")
                print(f"📥 Réponse brute:\n{resp_text}")
                data = json.loads(resp_text)
                text = ""
                try:
                    candidates = data.get("candidates", [])
                    if candidates:
                        content = (candidates[0] or {}).get("content", {})
                        parts = content.get("parts", []) or []
                        texts = [p.get("text") for p in parts if isinstance(p, dict) and p.get("text")]
                        text = "\n".join(texts)
                except Exception:
                    continue
                obj = _extract_json(text)
                activities = obj.get("activities", [])
                valid_activities = []
                for activity in activities:
                    if (isinstance(activity, dict) and 
                        activity.get('label') and 
                        len(activity['label']) > 3 and
                        activity.get('why')):
                        valid_activities.append({
                            'label': activity['label'].strip(),
                            'category': activity.get('category', 'bienetre').strip(),
                            'why': activity['why'].strip(),
                            'duration_min': activity.get('duration_min', 20)
                        })
                if valid_activities:
                    return {"activities": valid_activities[:3]}
                else:
                    pf = data.get("promptFeedback") or {}
                    br = pf.get("blockReason") or ""
                    if br:
                        return {"activities": [], "error": f"{mdl}: blocked ({br})"}
            except urllib.error.HTTPError as e:
                try:
                    error_body = e.read().decode('utf-8')
                    error_data = json.loads(error_body)
                    error_msg = f"HTTP {e.code}: {error_data.get('error', {}).get('message', 'Erreur inconnue')}"
                except:
                    error_msg = f"HTTP Error {e.code}"
                print(f"⚠️ {mdl} → {error_msg}")
                if e.code in [404, 429, 503]:
                    time.sleep(10 if e.code == 429 else 15)
                    continue
            except Exception as ex:
                return {"activities": [], "error": f"{mdl}: {ex}"}
        if attempt < max_retries - 1:
            time.sleep(10)

    return {"activities": [], "error": f"Aucun modèle Gemini compatible n'a pu générer de recommandations (essayés: {', '.join(models_to_try)})"}


def test_gemini_connection():
    print("🧪 TEST CONNEXION GEMINI...")

    class TestEntry:
        def get_mood_display(self): return "Heureux"
        energy_level = 4
        sleep_quality = 3
        main_subject = "Détente"
        content = "Belle journée de repos, j’ai pris le temps de me détendre, de lire un peu et de marcher."

    result = recommend_activities_gemini(TestEntry())
    print(f"📊 RÉSULTAT TEST: {result}")
    return result
