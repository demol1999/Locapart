from fastapi import Request, Response
from sqlalchemy.orm import Session
from database import SessionLocal
from audit_logger import AuditLogger
import models
import time
import json

class AuditMiddleware:
    """
    Middleware pour logger automatiquement toutes les requêtes API
    """
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Créer l'objet Request
        request = Request(scope, receive)
        
        # Variables pour le logging
        start_time = time.time()
        status_code = 200
        response_body = b""
        
        # Wrapper pour capturer la réponse
        async def send_wrapper(message):
            nonlocal status_code, response_body
            if message["type"] == "http.response.start":
                status_code = message["status"]
            elif message["type"] == "http.response.body":
                response_body += message.get("body", b"")
            await send(message)
        
        try:
            # Exécuter la requête
            await self.app(scope, receive, send_wrapper)
        except Exception as e:
            status_code = 500
            await send_wrapper({
                "type": "http.response.start",
                "status": 500,
                "headers": [(b"content-type", b"application/json")]
            })
            await send_wrapper({
                "type": "http.response.body",
                "body": json.dumps({"error": str(e)}).encode()
            })
        finally:
            # Calculer le temps de traitement
            process_time = time.time() - start_time
            
            # Logger la requête si nécessaire
            await self._log_request(request, status_code, process_time)
    
    async def _log_request(self, request: Request, status_code: int, process_time: float):
        """
        Log la requête si elle doit être loggée
        """
        # Ignorer certains endpoints (health checks, static files, etc.)
        ignore_paths = ["/docs", "/openapi.json", "/favicon.ico", "/uploads/"]
        
        if any(request.url.path.startswith(path) for path in ignore_paths):
            return
        
        # Ignorer les requêtes GET de consultation simple
        if request.method == "GET" and status_code == 200:
            return
        
        # Créer une session de base de données
        db = SessionLocal()
        try:
            # Récupérer l'utilisateur connecté si possible
            user_id = None
            try:
                # Extraire le token de l'en-tête Authorization
                auth_header = request.headers.get("authorization")
                if auth_header and auth_header.startswith("Bearer "):
                    from jose import jwt
                    from auth import SECRET_KEY, ALGORITHM
                    
                    token = auth_header.split(" ")[1]
                    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
                    email = payload.get("sub")
                    
                    if email:
                        user = db.query(models.UserAuth).filter(
                            models.UserAuth.email == email
                        ).first()
                        if user:
                            user_id = user.id
            except:
                pass  # Ignorer les erreurs de décodage de token
            
            # Déterminer l'action et l'entité basées sur l'endpoint
            action = self._get_action_from_method(request.method)
            entity_type = self._get_entity_from_path(request.url.path)
            
            # Description de l'action
            description = f"{request.method} {request.url.path}"
            if status_code >= 400:
                description += f" - Erreur {status_code}"
            
            # Détails de la requête
            details = {
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params) if request.query_params else None,
                "status_code": status_code,
                "process_time_ms": round(process_time * 1000, 2)
            }
            
            # Logger l'action
            AuditLogger.log_action(
                db=db,
                action=action,
                entity_type=entity_type,
                description=description,
                user_id=user_id,
                details=details,
                request=request,
                status_code=status_code
            )
            
        except Exception as e:
            print(f"Erreur lors du logging de la requête: {e}")
        finally:
            db.close()
    
    def _get_action_from_method(self, method: str) -> models.ActionType:
        """Convertit la méthode HTTP en type d'action"""
        method_mapping = {
            "GET": models.ActionType.READ,
            "POST": models.ActionType.CREATE,
            "PUT": models.ActionType.UPDATE,
            "PATCH": models.ActionType.UPDATE,
            "DELETE": models.ActionType.DELETE
        }
        return method_mapping.get(method, models.ActionType.READ)
    
    def _get_entity_from_path(self, path: str) -> models.EntityType:
        """Détermine le type d'entité basé sur le chemin"""
        if "/copros" in path:
            return models.EntityType.COPRO
        elif "/buildings" in path:
            return models.EntityType.BUILDING
        elif "/apartments" in path:
            return models.EntityType.APARTMENT
        elif "/syndicat" in path:
            return models.EntityType.SYNDICAT_COPRO
        elif "/upload" in path or "/photos" in path:
            return models.EntityType.PHOTO
        elif "/login" in path or "/logout" in path or "/refresh" in path:
            return models.EntityType.SESSION
        elif "/signup" in path or "/me" in path:
            return models.EntityType.USER
        else:
            return models.EntityType.USER  # Par défaut