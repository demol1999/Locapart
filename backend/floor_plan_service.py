"""
Service pour la gestion des plans 2D
"""
import os
import json
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional
from datetime import datetime
import base64
from PIL import Image, ImageDraw
import io

from models import FloorPlan


class FloorPlanService:
    """Service principal pour la gestion des plans 2D"""
    
    def __init__(self):
        self.upload_dir = "uploads/floor_plans"
        self.thumbnail_dir = f"{self.upload_dir}/thumbnails"
        self.exports_dir = f"{self.upload_dir}/exports"
        
        # Créer les dossiers si nécessaire
        os.makedirs(self.upload_dir, exist_ok=True)
        os.makedirs(self.thumbnail_dir, exist_ok=True)
        os.makedirs(self.exports_dir, exist_ok=True)
    
    def elements_to_xml(self, elements: List[Dict[str, Any]]) -> str:
        """Convertit une liste d'éléments en XML"""
        
        # Créer l'élément racine
        root = ET.Element("floorplan")
        root.set("version", "1.0")
        root.set("created", datetime.utcnow().isoformat())
        
        # Ajouter les métadonnées
        metadata = ET.SubElement(root, "metadata")
        ET.SubElement(metadata, "generator").text = "LocAppart Floor Plan Editor"
        ET.SubElement(metadata, "timestamp").text = datetime.utcnow().isoformat()
        
        # Ajouter les éléments
        elements_node = ET.SubElement(root, "elements")
        
        for element in elements:
            elem_node = ET.SubElement(elements_node, "element")
            elem_node.set("id", str(element.get("id", "")))
            elem_node.set("type", element.get("type", ""))
            
            # Propriétés spécifiques selon le type
            if element["type"] == "wall":
                wall_node = ET.SubElement(elem_node, "wall")
                
                # Points de départ et fin
                start_point = ET.SubElement(wall_node, "start_point")
                start_point.set("x", str(element["startPoint"]["x"]))
                start_point.set("y", str(element["startPoint"]["y"]))
                
                end_point = ET.SubElement(wall_node, "end_point")
                end_point.set("x", str(element["endPoint"]["x"]))
                end_point.set("y", str(element["endPoint"]["y"]))
                
                # Propriétés
                ET.SubElement(wall_node, "thickness").text = str(element.get("thickness", 10))
                
            elif element["type"] in ["door", "window"]:
                opening_node = ET.SubElement(elem_node, element["type"])
                opening_node.set("wall_id", str(element.get("wallId", "")))
                
                # Position sur le mur
                position = ET.SubElement(opening_node, "position")
                pos_data = element.get("position", {})
                position.set("x", str(pos_data.get("x", 0)))
                position.set("y", str(pos_data.get("y", 0)))
                position.set("t", str(pos_data.get("t", 0)))  # Position relative sur le mur
                
                # Dimensions
                ET.SubElement(opening_node, "width").text = str(element.get("width", 80))
                
                # Propriétés spécifiques
                properties = element.get("properties", {})
                if properties:
                    props_node = ET.SubElement(opening_node, "properties")
                    for key, value in properties.items():
                        if value is not None:
                            prop_elem = ET.SubElement(props_node, key)
                            prop_elem.text = str(value)
        
        # Convertir en string avec formatage
        rough_string = ET.tostring(root, encoding='unicode')
        return self._prettify_xml(rough_string)
    
    def xml_to_elements(self, xml_data: str) -> List[Dict[str, Any]]:
        """Convertit du XML en liste d'éléments"""
        try:
            root = ET.fromstring(xml_data)
            elements = []
            
            elements_node = root.find("elements")
            if elements_node is None:
                return elements
            
            for elem_node in elements_node.findall("element"):
                element_id = elem_node.get("id")
                element_type = elem_node.get("type")
                
                element = {
                    "id": element_id,
                    "type": element_type
                }
                
                if element_type == "wall":
                    wall_node = elem_node.find("wall")
                    if wall_node is not None:
                        # Points
                        start_point = wall_node.find("start_point")
                        end_point = wall_node.find("end_point")
                        
                        if start_point is not None and end_point is not None:
                            element["startPoint"] = {
                                "x": float(start_point.get("x", 0)),
                                "y": float(start_point.get("y", 0))
                            }
                            element["endPoint"] = {
                                "x": float(end_point.get("x", 0)),
                                "y": float(end_point.get("y", 0))
                            }
                        
                        # Propriétés
                        thickness_elem = wall_node.find("thickness")
                        if thickness_elem is not None:
                            element["thickness"] = int(thickness_elem.text or 10)
                        
                        element["properties"] = {}
                
                elif element_type in ["door", "window"]:
                    opening_node = elem_node.find(element_type)
                    if opening_node is not None:
                        element["wallId"] = opening_node.get("wall_id")
                        
                        # Position
                        position_node = opening_node.find("position")
                        if position_node is not None:
                            element["position"] = {
                                "x": float(position_node.get("x", 0)),
                                "y": float(position_node.get("y", 0)),
                                "t": float(position_node.get("t", 0))
                            }
                        
                        # Largeur
                        width_elem = opening_node.find("width")
                        if width_elem is not None:
                            element["width"] = int(width_elem.text or 80)
                        
                        # Propriétés spécifiques
                        props_node = opening_node.find("properties")
                        properties = {}
                        if props_node is not None:
                            for prop in props_node:
                                properties[prop.tag] = prop.text
                        element["properties"] = properties
                
                elements.append(element)
            
            return elements
            
        except ET.ParseError as e:
            print(f"Erreur de parsing XML: {e}")
            return []
    
    def parse_plan_data(self, plan: FloorPlan) -> Dict[str, Any]:
        """Parse les données XML d'un plan et retourne un objet enrichi"""
        
        elements = []
        if plan.xml_data:
            elements = self.xml_to_elements(plan.xml_data)
        
        return {
            "id": plan.id,
            "name": plan.name,
            "type": plan.type,
            "room_id": plan.room_id,
            "apartment_id": plan.apartment_id,
            "scale": plan.scale,
            "grid_size": plan.grid_size,
            "thumbnail_url": plan.thumbnail_url,
            "created_at": plan.created_at,
            "updated_at": plan.updated_at,
            "elements": elements,
            "metadata": {
                "walls_count": len([e for e in elements if e["type"] == "wall"]),
                "doors_count": len([e for e in elements if e["type"] == "door"]),
                "windows_count": len([e for e in elements if e["type"] == "window"]),
                "total_elements": len(elements)
            }
        }
    
    def generate_thumbnail(self, plan: FloorPlan, size: tuple = (300, 300)) -> str:
        """Génère une miniature du plan"""
        
        try:
            # Parse les éléments
            elements = []
            if plan.xml_data:
                elements = self.xml_to_elements(plan.xml_data)
            
            if not elements:
                # Générer une miniature vide
                return self._generate_empty_thumbnail(plan, size)
            
            # Calculer les bounds du plan
            min_x = min_y = float('inf')
            max_x = max_y = float('-inf')
            
            for element in elements:
                if element["type"] == "wall":
                    start_point = element.get("startPoint", {})
                    end_point = element.get("endPoint", {})
                    
                    min_x = min(min_x, start_point.get("x", 0), end_point.get("x", 0))
                    max_x = max(max_x, start_point.get("x", 0), end_point.get("x", 0))
                    min_y = min(min_y, start_point.get("y", 0), end_point.get("y", 0))
                    max_y = max(max_y, start_point.get("y", 0), end_point.get("y", 0))
            
            # Dimensions du plan
            plan_width = max_x - min_x if max_x > min_x else 100
            plan_height = max_y - min_y if max_y > min_y else 100
            
            # Créer l'image
            img = Image.new('RGB', size, 'white')
            draw = ImageDraw.Draw(img)
            
            # Calculer l'échelle pour s'adapter à la miniature
            scale_x = (size[0] - 20) / plan_width  # 10px de marge de chaque côté
            scale_y = (size[1] - 20) / plan_height
            scale = min(scale_x, scale_y)
            
            # Offset pour centrer
            offset_x = (size[0] - plan_width * scale) / 2
            offset_y = (size[1] - plan_height * scale) / 2
            
            def transform_point(x, y):
                return (
                    int((x - min_x) * scale + offset_x),
                    int((y - min_y) * scale + offset_y)
                )
            
            # Dessiner les murs
            for element in elements:
                if element["type"] == "wall":
                    start_point = element.get("startPoint", {})
                    end_point = element.get("endPoint", {})
                    thickness = element.get("thickness", 10)
                    
                    start_x, start_y = transform_point(start_point.get("x", 0), start_point.get("y", 0))
                    end_x, end_y = transform_point(end_point.get("x", 0), end_point.get("y", 0))
                    
                    # Adapter l'épaisseur à l'échelle
                    line_width = max(1, int(thickness * scale / 5))
                    
                    draw.line([(start_x, start_y), (end_x, end_y)], fill='black', width=line_width)
            
            # Dessiner les ouvertures (simplifié)
            for element in elements:
                if element["type"] in ["door", "window"]:
                    position = element.get("position", {})
                    pos_x, pos_y = transform_point(position.get("x", 0), position.get("y", 0))
                    
                    color = 'blue' if element["type"] == "door" else 'cyan'
                    radius = max(2, int(5 * scale))
                    
                    draw.ellipse([
                        pos_x - radius, pos_y - radius,
                        pos_x + radius, pos_y + radius
                    ], fill=color)
            
            # Sauvegarder
            filename = f"plan_{plan.id}_{int(datetime.now().timestamp())}.png"
            filepath = os.path.join(self.thumbnail_dir, filename)
            img.save(filepath, 'PNG', quality=85)
            
            # Retourner l'URL relative
            return f"/uploads/floor_plans/thumbnails/{filename}"
            
        except Exception as e:
            print(f"Erreur génération miniature: {e}")
            return self._generate_empty_thumbnail(plan, size)
    
    def _generate_empty_thumbnail(self, plan: FloorPlan, size: tuple) -> str:
        """Génère une miniature vide"""
        img = Image.new('RGB', size, 'white')
        draw = ImageDraw.Draw(img)
        
        # Dessiner un cadre
        draw.rectangle([5, 5, size[0]-5, size[1]-5], outline='gray', width=2)
        
        # Texte centré
        text = "Plan vide"
        bbox = draw.textbbox((0, 0), text)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        text_x = (size[0] - text_width) // 2
        text_y = (size[1] - text_height) // 2
        
        draw.text((text_x, text_y), text, fill='gray')
        
        filename = f"plan_empty_{plan.id}_{int(datetime.now().timestamp())}.png"
        filepath = os.path.join(self.thumbnail_dir, filename)
        img.save(filepath, 'PNG')
        
        return f"/uploads/floor_plans/thumbnails/{filename}"
    
    def export_to_svg(self, plan: FloorPlan) -> str:
        """Exporte un plan en SVG"""
        
        elements = []
        if plan.xml_data:
            elements = self.xml_to_elements(plan.xml_data)
        
        # Calculer les bounds
        min_x = min_y = float('inf')
        max_x = max_y = float('-inf')
        
        for element in elements:
            if element["type"] == "wall":
                start_point = element.get("startPoint", {})
                end_point = element.get("endPoint", {})
                
                min_x = min(min_x, start_point.get("x", 0), end_point.get("x", 0))
                max_x = max(max_x, start_point.get("x", 0), end_point.get("x", 0))
                min_y = min(min_y, start_point.get("y", 0), end_point.get("y", 0))
                max_y = max(max_y, start_point.get("y", 0), end_point.get("y", 0))
        
        # Dimensions
        width = max_x - min_x + 100 if max_x > min_x else 200
        height = max_y - min_y + 100 if max_y > min_y else 200
        
        # Générer le SVG
        svg_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="{min_x-50} {min_y-50} {width} {height}">
  <title>{plan.name}</title>
  <desc>Plan généré par LocAppart - {datetime.now().strftime("%Y-%m-%d %H:%M")}</desc>
  
  <!-- Grille de fond -->
  <defs>
    <pattern id="grid" width="{plan.grid_size or 20}" height="{plan.grid_size or 20}" patternUnits="userSpaceOnUse">
      <path d="M {plan.grid_size or 20} 0 L 0 0 0 {plan.grid_size or 20}" fill="none" stroke="#e0e0e0" stroke-width="0.5"/>
    </pattern>
  </defs>
  <rect width="100%" height="100%" fill="url(#grid)" />
  
  <!-- Éléments du plan -->
'''
        
        # Ajouter les murs
        for element in elements:
            if element["type"] == "wall":
                start_point = element.get("startPoint", {})
                end_point = element.get("endPoint", {})
                thickness = element.get("thickness", 10)
                
                svg_content += f'''  <line x1="{start_point.get('x', 0)}" y1="{start_point.get('y', 0)}" x2="{end_point.get('x', 0)}" y2="{end_point.get('y', 0)}" stroke="#333" stroke-width="{thickness}" stroke-linecap="round" />
'''
        
        # Ajouter les ouvertures
        for element in elements:
            if element["type"] == "door":
                position = element.get("position", {})
                svg_content += f'''  <circle cx="{position.get('x', 0)}" cy="{position.get('y', 0)}" r="3" fill="#4ecdc4" />
'''
            elif element["type"] == "window":
                position = element.get("position", {})
                svg_content += f'''  <circle cx="{position.get('x', 0)}" cy="{position.get('y', 0)}" r="3" fill="#4dabf7" />
'''
        
        svg_content += '</svg>'
        
        return svg_content
    
    def export_to_png(self, plan: FloorPlan, size: tuple = (1920, 1080)) -> bytes:
        """Exporte un plan en PNG haute résolution"""
        
        elements = []
        if plan.xml_data:
            elements = self.xml_to_elements(plan.xml_data)
        
        if not elements:
            # Image vide
            img = Image.new('RGB', size, 'white')
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            return buffer.getvalue()
        
        # Calculer les bounds
        min_x = min_y = float('inf')
        max_x = max_y = float('-inf')
        
        for element in elements:
            if element["type"] == "wall":
                start_point = element.get("startPoint", {})
                end_point = element.get("endPoint", {})
                
                min_x = min(min_x, start_point.get("x", 0), end_point.get("x", 0))
                max_x = max(max_x, start_point.get("x", 0), end_point.get("x", 0))
                min_y = min(min_y, start_point.get("y", 0), end_point.get("y", 0))
                max_y = max(max_y, start_point.get("y", 0), end_point.get("y", 0))
        
        # Dimensions du plan
        plan_width = max_x - min_x if max_x > min_x else 100
        plan_height = max_y - min_y if max_y > min_y else 100
        
        # Créer l'image
        img = Image.new('RGB', size, 'white')
        draw = ImageDraw.Draw(img)
        
        # Calculer l'échelle
        margin = 100
        scale_x = (size[0] - 2 * margin) / plan_width
        scale_y = (size[1] - 2 * margin) / plan_height
        scale = min(scale_x, scale_y)
        
        # Offset pour centrer
        offset_x = (size[0] - plan_width * scale) / 2
        offset_y = (size[1] - plan_height * scale) / 2
        
        def transform_point(x, y):
            return (
                int((x - min_x) * scale + offset_x),
                int((y - min_y) * scale + offset_y)
            )
        
        # Dessiner les éléments
        for element in elements:
            if element["type"] == "wall":
                start_point = element.get("startPoint", {})
                end_point = element.get("endPoint", {})
                thickness = element.get("thickness", 10)
                
                start_x, start_y = transform_point(start_point.get("x", 0), start_point.get("y", 0))
                end_x, end_y = transform_point(end_point.get("x", 0), end_point.get("y", 0))
                
                line_width = max(2, int(thickness * scale / 2))
                draw.line([(start_x, start_y), (end_x, end_y)], fill='black', width=line_width)
        
        # Sauvegarder en buffer
        buffer = io.BytesIO()
        img.save(buffer, format='PNG', quality=95)
        return buffer.getvalue()
    
    def export_to_pdf(self, plan: FloorPlan) -> bytes:
        """Exporte un plan en PDF (simplifié)"""
        # Pour une implémentation complète, utiliser reportlab
        # Ici on retourne un PNG pour le moment
        png_data = self.export_to_png(plan)
        return png_data
    
    def cleanup_plan_files(self, plan: FloorPlan):
        """Nettoie les fichiers associés à un plan"""
        try:
            # Supprimer la miniature
            if plan.thumbnail_url:
                thumbnail_path = plan.thumbnail_url.replace("/uploads/floor_plans/thumbnails/", "")
                full_path = os.path.join(self.thumbnail_dir, thumbnail_path)
                if os.path.exists(full_path):
                    os.remove(full_path)
            
            # Supprimer les exports éventuels
            export_pattern = f"plan_{plan.id}_*"
            for filename in os.listdir(self.exports_dir):
                if filename.startswith(f"plan_{plan.id}_"):
                    os.remove(os.path.join(self.exports_dir, filename))
                    
        except Exception as e:
            print(f"Erreur nettoyage fichiers: {e}")
    
    def get_template(self, template_type: str) -> Dict[str, Any]:
        """Retourne un template de plan prédéfini"""
        
        templates = {
            "T1": {
                "name": f"Template T1 - Studio",
                "elements": [
                    # Murs extérieurs
                    {
                        "id": "wall_1",
                        "type": "wall",
                        "startPoint": {"x": 0, "y": 0},
                        "endPoint": {"x": 400, "y": 0},
                        "thickness": 15,
                        "properties": {}
                    },
                    {
                        "id": "wall_2",
                        "type": "wall",
                        "startPoint": {"x": 400, "y": 0},
                        "endPoint": {"x": 400, "y": 300},
                        "thickness": 15,
                        "properties": {}
                    },
                    {
                        "id": "wall_3",
                        "type": "wall",
                        "startPoint": {"x": 400, "y": 300},
                        "endPoint": {"x": 0, "y": 300},
                        "thickness": 15,
                        "properties": {}
                    },
                    {
                        "id": "wall_4",
                        "type": "wall",
                        "startPoint": {"x": 0, "y": 300},
                        "endPoint": {"x": 0, "y": 0},
                        "thickness": 15,
                        "properties": {}
                    },
                    # Cloison salle de bain
                    {
                        "id": "wall_5",
                        "type": "wall",
                        "startPoint": {"x": 280, "y": 0},
                        "endPoint": {"x": 280, "y": 120},
                        "thickness": 10,
                        "properties": {}
                    },
                    # Porte d'entrée
                    {
                        "id": "door_1",
                        "type": "door",
                        "wallId": "wall_1",
                        "position": {"x": 80, "y": 0, "t": 0.2},
                        "width": 80,
                        "properties": {"opening": "inward-right"}
                    },
                    # Porte salle de bain
                    {
                        "id": "door_2",
                        "type": "door",
                        "wallId": "wall_5",
                        "position": {"x": 280, "y": 60, "t": 0.5},
                        "width": 70,
                        "properties": {"opening": "outward-left"}
                    },
                    # Fenêtre
                    {
                        "id": "window_1",
                        "type": "window",
                        "wallId": "wall_2",
                        "position": {"x": 400, "y": 150, "t": 0.5},
                        "width": 120,
                        "properties": {"height": 10}
                    }
                ]
            },
            "T2": {
                "name": f"Template T2 - 2 pièces",
                "elements": [
                    # Structure de base plus complexe pour un T2
                    # Murs extérieurs
                    {
                        "id": "wall_1",
                        "type": "wall",
                        "startPoint": {"x": 0, "y": 0},
                        "endPoint": {"x": 500, "y": 0},
                        "thickness": 15,
                        "properties": {}
                    },
                    {
                        "id": "wall_2",
                        "type": "wall",
                        "startPoint": {"x": 500, "y": 0},
                        "endPoint": {"x": 500, "y": 400},
                        "thickness": 15,
                        "properties": {}
                    },
                    {
                        "id": "wall_3",
                        "type": "wall",
                        "startPoint": {"x": 500, "y": 400},
                        "endPoint": {"x": 0, "y": 400},
                        "thickness": 15,
                        "properties": {}
                    },
                    {
                        "id": "wall_4",
                        "type": "wall",
                        "startPoint": {"x": 0, "y": 400},
                        "endPoint": {"x": 0, "y": 0},
                        "thickness": 15,
                        "properties": {}
                    },
                    # Cloison chambre
                    {
                        "id": "wall_5",
                        "type": "wall",
                        "startPoint": {"x": 300, "y": 0},
                        "endPoint": {"x": 300, "y": 250},
                        "thickness": 10,
                        "properties": {}
                    },
                    # Cloison salle de bain
                    {
                        "id": "wall_6",
                        "type": "wall",
                        "startPoint": {"x": 350, "y": 250},
                        "endPoint": {"x": 500, "y": 250},
                        "thickness": 10,
                        "properties": {}
                    }
                ]
            }
        }
        
        if template_type not in templates:
            raise ValueError(f"Template '{template_type}' non trouvé")
        
        return templates[template_type]
    
    def _prettify_xml(self, elem_str: str) -> str:
        """Formate le XML de manière lisible"""
        try:
            import xml.dom.minidom
            dom = xml.dom.minidom.parseString(elem_str)
            return dom.toprettyxml(indent="  ", encoding=None)
        except:
            return elem_str