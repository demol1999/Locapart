"""
Rate Limiter pour protection contre les attaques de force brute
"""
import time
from typing import Dict, Optional
from datetime import datetime, timedelta
from fastapi import HTTPException, Request
import redis
import json
import os

class RateLimiter:
    """Limiteur de taux d'attaques"""
    
    def __init__(self):
        # Utiliser Redis si disponible, sinon mémoire locale (dev seulement)
        self.redis_url = os.getenv("REDIS_URL")
        if self.redis_url:
            try:
                import redis
                self.redis_client = redis.from_url(self.redis_url)
                self.use_redis = True
            except ImportError:
                self.use_redis = False
                self.memory_store = {}
        else:
            self.use_redis = False
            self.memory_store = {}
        
        # Configuration des limites
        self.limits = {
            "login": {"requests": 5, "window": 300},      # 5 tentatives par 5 minutes
            "signup": {"requests": 3, "window": 3600},    # 3 inscriptions par heure
            "api": {"requests": 100, "window": 60},       # 100 requêtes par minute
            "upload": {"requests": 10, "window": 60}      # 10 uploads par minute
        }
    
    def get_client_id(self, request: Request) -> str:
        """Obtient l'identifiant unique du client"""
        # Utiliser l'IP + User-Agent pour l'identification
        ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "")[:100]  # Limiter la taille
        return f"{ip}:{hash(user_agent) % 10000}"
    
    def _get_key(self, client_id: str, endpoint: str) -> str:
        """Génère la clé de stockage"""
        return f"rate_limit:{endpoint}:{client_id}"
    
    def _get_count(self, key: str) -> Dict:
        """Récupère le compteur actuel"""
        if self.use_redis:
            try:
                data = self.redis_client.get(key)
                return json.loads(data) if data else {"count": 0, "window_start": time.time()}
            except:
                return {"count": 0, "window_start": time.time()}
        else:
            return self.memory_store.get(key, {"count": 0, "window_start": time.time()})
    
    def _set_count(self, key: str, data: Dict, ttl: int):
        """Stocke le compteur"""
        if self.use_redis:
            try:
                self.redis_client.setex(key, ttl, json.dumps(data))
            except:
                pass
        else:
            data["expires"] = time.time() + ttl
            self.memory_store[key] = data
            
            # Nettoyage de la mémoire
            current_time = time.time()
            self.memory_store = {
                k: v for k, v in self.memory_store.items() 
                if v.get("expires", current_time) > current_time
            }
    
    def check_rate_limit(self, request: Request, endpoint: str) -> bool:
        """Vérifie si la limite est atteinte"""
        if endpoint not in self.limits:
            return True
        
        client_id = self.get_client_id(request)
        key = self._get_key(client_id, endpoint)
        limit_config = self.limits[endpoint]
        
        current_time = time.time()
        data = self._get_count(key)
        
        # Vérifier si on est dans une nouvelle fenêtre
        if current_time - data["window_start"] >= limit_config["window"]:
            # Nouvelle fenêtre
            data = {"count": 1, "window_start": current_time}
        else:
            # Même fenêtre
            data["count"] += 1
        
        # Sauvegarder
        self._set_count(key, data, limit_config["window"])
        
        # Vérifier la limite
        if data["count"] > limit_config["requests"]:
            time_remaining = limit_config["window"] - (current_time - data["window_start"])
            raise HTTPException(
                status_code=429,
                detail=f"Trop de tentatives. Réessayez dans {int(time_remaining)} secondes.",
                headers={"Retry-After": str(int(time_remaining))}
            )
        
        return True

# Instance globale
rate_limiter = RateLimiter()

def check_rate_limit(endpoint: str):
    """Décorateur pour vérifier les limites de taux"""
    def decorator(request: Request):
        rate_limiter.check_rate_limit(request, endpoint)
        return True
    return decorator