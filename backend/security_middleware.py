"""
Middleware de sécurité avancé pour LocAppart
"""
import time
import hashlib
import hmac
import os
from typing import Set
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

class SecurityMiddleware(BaseHTTPMiddleware):
    """Middleware de sécurité avancé"""
    
    def __init__(self, app, allowed_hosts: Set[str] = None):
        super().__init__(app)
        self.allowed_hosts = allowed_hosts or {"localhost", "127.0.0.1"}
        self.blocked_ips: Set[str] = set()
        self.suspicious_patterns = [
            # Patterns d'attaques communes
            r'<script',
            r'javascript:',
            r'eval\(',
            r'union.*select',
            r'drop.*table',
            r'../../../',
            r'\.\./',
            r'cmd=',
            r'exec\(',
            r'system\(',
        ]
    
    async def dispatch(self, request: Request, call_next):
        """Traite chaque requête"""
        
        # 1. Vérification de l'host
        if not self._check_host(request):
            raise HTTPException(status_code=400, detail="Host non autorisé")
        
        # 2. Vérification IP blacklist
        client_ip = self._get_client_ip(request)
        if client_ip in self.blocked_ips:
            raise HTTPException(status_code=403, detail="Accès refusé")
        
        # 3. Détection d'attaques
        if self._detect_attack_patterns(request):
            self._log_suspicious_activity(request)
            raise HTTPException(status_code=400, detail="Requête suspecte détectée")
        
        # 4. Limite de taille des requêtes
        if not self._check_request_size(request):
            raise HTTPException(status_code=413, detail="Requête trop volumineuse")
        
        # 5. Traiter la requête
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # 6. Ajouter headers de sécurité
        self._add_security_headers(response)
        
        # 7. Logger les temps de réponse lents (potentielle attaque DoS)
        if process_time > 5.0:  # Plus de 5 secondes
            self._log_slow_request(request, process_time)
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Obtient la vraie IP du client"""
        # Vérifier les headers de proxy
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"
    
    def _check_host(self, request: Request) -> bool:
        """Vérifie que l'host est autorisé"""
        host = request.headers.get("host", "")
        host_without_port = host.split(":")[0]
        return host_without_port in self.allowed_hosts
    
    def _detect_attack_patterns(self, request: Request) -> bool:
        """Détecte les patterns d'attaques communes"""
        import re
        
        # Vérifier l'URL
        url_str = str(request.url)
        for pattern in self.suspicious_patterns:
            if re.search(pattern, url_str, re.IGNORECASE):
                return True
        
        # Vérifier les headers
        for header_name, header_value in request.headers.items():
            for pattern in self.suspicious_patterns:
                if re.search(pattern, header_value, re.IGNORECASE):
                    return True
        
        # Vérifier User-Agent suspect
        user_agent = request.headers.get("user-agent", "")
        suspicious_agents = ["sqlmap", "nmap", "nikto", "dirb", "gobuster", "curl/7"]
        if any(agent in user_agent.lower() for agent in suspicious_agents):
            return True
        
        return False
    
    def _check_request_size(self, request: Request) -> bool:
        """Vérifie la taille de la requête"""
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                size = int(content_length)
                # Limite à 50MB (sauf pour uploads)
                max_size = 50 * 1024 * 1024
                if "/upload" in str(request.url):
                    max_size = 100 * 1024 * 1024  # 100MB pour uploads
                return size <= max_size
            except ValueError:
                return False
        return True
    
    def _add_security_headers(self, response: Response):
        """Ajoute des headers de sécurité supplémentaires"""
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["X-Download-Options"] = "noopen"
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        
        # Header personnalisé pour identifier l'application
        response.headers["X-Powered-By"] = "LocAppart-Secure"
    
    def _log_suspicious_activity(self, request: Request):
        """Log une activité suspecte"""
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "unknown")
        
        print(f"🚨 ACTIVITÉ SUSPECTE DÉTECTÉE:")
        print(f"   IP: {client_ip}")
        print(f"   URL: {request.url}")
        print(f"   User-Agent: {user_agent}")
        print(f"   Method: {request.method}")
        
        # Ajouter à la blacklist temporaire après 3 tentatives
        # (En production, utiliser Redis ou base de données)
        
    def _log_slow_request(self, request: Request, process_time: float):
        """Log une requête lente"""
        client_ip = self._get_client_ip(request)
        print(f"⚠️  REQUÊTE LENTE DÉTECTÉE:")
        print(f"   IP: {client_ip}")
        print(f"   URL: {request.url}")
        print(f"   Temps: {process_time:.2f}s")

def create_security_middleware(allowed_hosts: Set[str] = None):
    """Factory pour créer le middleware de sécurité"""
    if not allowed_hosts:
        # Récupérer depuis les variables d'environnement
        hosts_env = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1")
        allowed_hosts = set(host.strip() for host in hosts_env.split(","))
    
    return SecurityMiddleware(None, allowed_hosts)