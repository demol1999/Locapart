import React, { useState, useRef, useEffect, useCallback } from 'react';

const FloorPlanEditor = ({ 
  planData = null, 
  onSave = () => {}, 
  onExport = () => {},
  width = 1000, 
  height = 700,
  readonly = false 
}) => {
  // ==================== SYSTÈME D'UNITÉS ====================
  const [currentUnit, setCurrentUnit] = useState('meters'); // meters, inches, feet
  const [scale, setScale] = useState(1);
  const [pixelsPerUnit, setPixelsPerUnit] = useState(100); // 100px = 1 mètre par défaut
  
  // Conversions d'unités
  const unitConversions = {
    meters: { name: 'Mètres', symbol: 'm', factor: 1, pixelsPerUnit: 100 },
    inches: { name: 'Pouces', symbol: 'in', factor: 39.3701, pixelsPerUnit: 10 }, // 1m = 39.37 inches
    feet: { name: 'Pieds', symbol: 'ft', factor: 3.28084, pixelsPerUnit: 30 } // 1m = 3.28 feet
  };

  // Convertir les pixels en unités réelles
  const pixelsToUnits = useCallback((pixels) => {
    const baseMeters = pixels / unitConversions.meters.pixelsPerUnit;
    return baseMeters * unitConversions[currentUnit].factor;
  }, [currentUnit]);

  // Convertir les unités réelles en pixels
  const unitsToPixels = useCallback((units) => {
    const meters = units / unitConversions[currentUnit].factor;
    return meters * unitConversions.meters.pixelsPerUnit;
  }, [currentUnit]);

  // Formater la valeur avec l'unité
  const formatMeasurement = useCallback((pixels) => {
    const value = pixelsToUnits(pixels);
    const unit = unitConversions[currentUnit];
    return `${value.toFixed(2)}${unit.symbol}`;
  }, [pixelsToUnits, currentUnit]);

  // ==================== ÉTAT PRINCIPAL ====================
  const [elements, setElements] = useState([]);
  const [selectedElement, setSelectedElement] = useState(null);
  const [currentTool, setCurrentTool] = useState('select');
  const [isDrawing, setIsDrawing] = useState(false);
  const [drawingData, setDrawingData] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [dragData, setDragData] = useState(null);
  
  // Configuration
  const [panOffset, setPanOffset] = useState({ x: 0, y: 0 });
  const [gridSize, setGridSize] = useState(50); // Grille basée sur les unités réelles
  const [showGrid, setShowGrid] = useState(true);
  const [snapToGrid, setSnapToGrid] = useState(true);
  const [showMeasurements, setShowMeasurements] = useState(true);
  
  // Propriétés des éléments par défaut (en unités réelles)
  const [wallThickness, setWallThickness] = useState(0.2); // 20cm
  const [doorWidth, setDoorWidth] = useState(0.8); // 80cm
  const [doorHeight, setDoorHeight] = useState(2.0); // 2m
  const [windowWidth, setWindowWidth] = useState(1.2); // 120cm
  const [windowHeight, setWindowHeight] = useState(1.0); // 100cm
  
  // Références
  const svgRef = useRef(null);
  const containerRef = useRef(null);
  const editorRef = useRef(null);
  const [viewBox, setViewBox] = useState(`0 0 ${width} ${height}`);

  // ==================== OUTILS ====================
  const tools = {
    select: { icon: '↖️', name: 'Sélection', cursor: 'default' },
    wall: { icon: '🧱', name: 'Mur', cursor: 'crosshair' },
    door: { icon: '🚪', name: 'Porte', cursor: 'crosshair' },
    window: { icon: '🪟', name: 'Fenêtre', cursor: 'crosshair' },
    measure: { icon: '📏', name: 'Règle', cursor: 'crosshair' },
    erase: { icon: '🗑️', name: 'Supprimer', cursor: 'crosshair' }
  };

  // ==================== FONCTIONS UTILITAIRES ====================
  const snapToGridPoint = useCallback((point) => {
    if (!snapToGrid) return point;
    const gridPixels = unitsToPixels(gridSize / 100); // Grille de 0.5m par défaut
    return {
      x: Math.round(point.x / gridPixels) * gridPixels,
      y: Math.round(point.y / gridPixels) * gridPixels
    };
  }, [snapToGrid, gridSize, unitsToPixels]);

  const getSVGPoint = useCallback((clientX, clientY) => {
    if (!svgRef.current) return { x: 0, y: 0 };
    
    const rect = svgRef.current.getBoundingClientRect();
    const x = (clientX - rect.left) / scale - panOffset.x;
    const y = (clientY - rect.top) / scale - panOffset.y;
    
    return snapToGridPoint({ x, y });
  }, [scale, panOffset, snapToGridPoint]);

  const generateId = () => {
    return 'elem_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
  };

  // Forcer les angles droits pour les murs
  const enforceRightAngles = useCallback((startPoint, currentPoint) => {
    const dx = Math.abs(currentPoint.x - startPoint.x);
    const dy = Math.abs(currentPoint.y - startPoint.y);
    
    if (dx > dy) {
      // Ligne horizontale
      return { x: currentPoint.x, y: startPoint.y };
    } else {
      // Ligne verticale  
      return { x: startPoint.x, y: currentPoint.y };
    }
  }, []);

  // Trouver un élément à un point donné
  const findElementAtPoint = useCallback((point, tolerance = 5) => {
    return elements.find(element => {
      if (element.type === 'wall') {
        // Distance point-ligne pour les murs
        const { startPoint, endPoint } = element;
        const A = point.x - startPoint.x;
        const B = point.y - startPoint.y;
        const C = endPoint.x - startPoint.x;
        const D = endPoint.y - startPoint.y;
        
        const dot = A * C + B * D;
        const lenSq = C * C + D * D;
        const param = lenSq !== 0 ? dot / lenSq : -1;
        
        let xx, yy;
        if (param < 0) {
          xx = startPoint.x;
          yy = startPoint.y;
        } else if (param > 1) {
          xx = endPoint.x;
          yy = endPoint.y;
        } else {
          xx = startPoint.x + param * C;
          yy = startPoint.y + param * D;
        }
        
        const dx = point.x - xx;
        const dy = point.y - yy;
        return Math.sqrt(dx * dx + dy * dy) <= tolerance + element.thickness / 2;
      }
      return false;
    });
  }, [elements]);

  // ==================== ÉVÉNEMENTS SOURIS ====================
  const handleMouseDown = useCallback((e) => {
    if (readonly) return;
    
    const point = getSVGPoint(e.clientX, e.clientY);
    
    if (currentTool === 'select') {
      const element = findElementAtPoint(point);
      setSelectedElement(element);
      
      if (element && e.target.classList.contains('resize-handle')) {
        setIsDragging(true);
        setDragData({
          element,
          startPoint: point,
          handleType: e.target.dataset.handle
        });
      }
    } else if (currentTool === 'wall') {
      setIsDrawing(true);
      setDrawingData({
        startPoint: point,
        currentPoint: point,
        type: 'wall'
      });
    } else if (currentTool === 'door' || currentTool === 'window') {
      // Placement automatique sur le mur le plus proche
      const targetWall = findElementAtPoint(point, 20);
      if (targetWall && targetWall.type === 'wall') {
        const newElement = {
          id: generateId(),
          type: currentTool,
          wallId: targetWall.id,
          position: point,
          width: currentTool === 'door' ? doorWidth : windowWidth,
          height: currentTool === 'door' ? doorHeight : windowHeight,
          properties: {
            opening: currentTool === 'door' ? 'inward-left' : null
          }
        };
        setElements(prev => [...prev, newElement]);
      }
    } else if (currentTool === 'measure') {
      setIsDrawing(true);
      setDrawingData({
        startPoint: point,
        currentPoint: point,
        type: 'measure'
      });
    } else if (currentTool === 'erase') {
      const element = findElementAtPoint(point);
      if (element) {
        setElements(prev => prev.filter(el => el.id !== element.id));
        setSelectedElement(null);
      }
    }
  }, [currentTool, readonly, getSVGPoint, findElementAtPoint, doorWidth, doorHeight, windowWidth, windowHeight]);

  const handleMouseMove = useCallback((e) => {
    if (readonly) return;
    
    const point = getSVGPoint(e.clientX, e.clientY);
    
    if (isDrawing && drawingData) {
      let updatedPoint = point;
      
      if (drawingData.type === 'wall') {
        // Forcer les angles droits
        updatedPoint = enforceRightAngles(drawingData.startPoint, point);
      }
      
      setDrawingData(prev => ({
        ...prev,
        currentPoint: updatedPoint
      }));
    } else if (isDragging && dragData) {
      // Logique de redimensionnement
      const { element, handleType, startPoint } = dragData;
      const dx = point.x - startPoint.x;
      const dy = point.y - startPoint.y;
      
      // Mise à jour de l'élément en cours de redimensionnement
      setElements(prev => prev.map(el => {
        if (el.id === element.id) {
          if (el.type === 'wall') {
            if (handleType === 'start') {
              return { ...el, startPoint: point };
            } else if (handleType === 'end') {
              return { ...el, endPoint: point };
            }
          }
        }
        return el;
      }));
    }
  }, [readonly, getSVGPoint, isDrawing, drawingData, isDragging, dragData, enforceRightAngles]);

  const handleMouseUp = useCallback((e) => {
    if (readonly) return;
    
    if (isDrawing && drawingData) {
      const point = getSVGPoint(e.clientX, e.clientY);
      
      if (drawingData.type === 'wall') {
        const { startPoint } = drawingData;
        const endPoint = enforceRightAngles(startPoint, point);
        
        // Éviter les murs trop petits
        const distance = Math.sqrt(
          Math.pow(endPoint.x - startPoint.x, 2) + Math.pow(endPoint.y - startPoint.y, 2)
        );
        
        if (distance > 20) {
          const newWall = {
            id: generateId(),
            type: 'wall',
            startPoint,
            endPoint,
            thickness: unitsToPixels(wallThickness),
            properties: {}
          };
          setElements(prev => [...prev, newWall]);
        }
      } else if (drawingData.type === 'measure') {
        const { startPoint } = drawingData;
        const distance = Math.sqrt(
          Math.pow(point.x - startPoint.x, 2) + Math.pow(point.y - startPoint.y, 2)
        );
        
        if (distance > 10) {
          const newMeasure = {
            id: generateId(),
            type: 'measure',
            startPoint,
            endPoint: point,
            measurement: formatMeasurement(distance),
            properties: {}
          };
          setElements(prev => [...prev, newMeasure]);
        }
      }
      
      setIsDrawing(false);
      setDrawingData(null);
    }
    
    if (isDragging) {
      setIsDragging(false);
      setDragData(null);
    }
  }, [readonly, getSVGPoint, isDrawing, drawingData, isDragging, enforceRightAngles, unitsToPixels, wallThickness, formatMeasurement]);

  // ==================== RENDU DES ÉLÉMENTS ====================
  const renderWall = (wall) => {
    const { startPoint, endPoint, thickness, id } = wall;
    const isSelected = selectedElement?.id === id;
    
    // Calcul du vecteur perpendiculaire pour l'épaisseur
    const dx = endPoint.x - startPoint.x;
    const dy = endPoint.y - startPoint.y;
    const length = Math.sqrt(dx * dx + dy * dy);
    const unitX = dx / length;
    const unitY = dy / length;
    const perpX = -unitY * thickness / 2;
    const perpY = unitX * thickness / 2;
    
    const points = [
      `${startPoint.x + perpX},${startPoint.y + perpY}`,
      `${endPoint.x + perpX},${endPoint.y + perpY}`,
      `${endPoint.x - perpX},${endPoint.y - perpY}`,
      `${startPoint.x - perpX},${startPoint.y - perpY}`
    ].join(' ');
    
    return (
      <g key={id}>
        <polygon
          points={points}
          fill="#444444"
          stroke={isSelected ? "#007bff" : "#333333"}
          strokeWidth={isSelected ? 2 : 1}
          style={{ cursor: 'pointer' }}
          onClick={(e) => {
            e.stopPropagation();
            setSelectedElement(wall);
          }}
        />
        
        {/* Poignées de redimensionnement si sélectionné */}
        {isSelected && (
          <>
            <circle
              cx={startPoint.x}
              cy={startPoint.y}
              r="6"
              fill="#007bff"
              stroke="white"
              strokeWidth="2"
              className="resize-handle"
              data-handle="start"
              style={{ cursor: 'move' }}
            />
            <circle
              cx={endPoint.x}
              cy={endPoint.y}
              r="6"
              fill="#007bff"
              stroke="white"
              strokeWidth="2"
              className="resize-handle"
              data-handle="end"
              style={{ cursor: 'move' }}
            />
          </>
        )}
        
        {/* Affichage des mesures */}
        {showMeasurements && (
          <text
            x={(startPoint.x + endPoint.x) / 2}
            y={(startPoint.y + endPoint.y) / 2 - 10}
            textAnchor="middle"
            fontSize="12"
            fill="#666"
            className="measurement-text"
          >
            {formatMeasurement(length)}
          </text>
        )}
      </g>
    );
  };

  const renderDoor = (door) => {
    const { position, width, height, id, wallId } = door;
    const isSelected = selectedElement?.id === id;
    const wall = elements.find(el => el.id === wallId);
    
    if (!wall) return null;
    
    // Calculer la position et l'orientation basée sur le mur
    const wallDx = wall.endPoint.x - wall.startPoint.x;
    const wallDy = wall.endPoint.y - wall.startPoint.y;
    const wallLength = Math.sqrt(wallDx * wallDx + wallDy * wallDy);
    const wallUnitX = wallDx / wallLength;
    const wallUnitY = wallDy / wallLength;
    
    const doorPixelWidth = unitsToPixels(width);
    const doorPixelHeight = unitsToPixels(height);
    
    return (
      <g key={id}>
        <rect
          x={position.x - doorPixelWidth / 2}
          y={position.y - wall.thickness / 2}
          width={doorPixelWidth}
          height={wall.thickness}
          fill="#8B4513" // Couleur marron pour les portes
          stroke={isSelected ? "#007bff" : "#654321"}
          strokeWidth={isSelected ? 2 : 1}
          rx="0" // Coins droits
          style={{ cursor: 'pointer' }}
          onClick={(e) => {
            e.stopPropagation();
            setSelectedElement(door);
          }}
        />
        
        {/* Poignée de porte */}
        <circle
          cx={position.x + doorPixelWidth / 3}
          cy={position.y}
          r="2"
          fill="#FFD700"
        />
        
        {isSelected && (
          <circle
            cx={position.x}
            cy={position.y}
            r="6"
            fill="#007bff"
            stroke="white"
            strokeWidth="2"
            style={{ cursor: 'move' }}
          />
        )}
      </g>
    );
  };

  const renderWindow = (window) => {
    const { position, width, height, id, wallId } = window;
    const isSelected = selectedElement?.id === id;
    const wall = elements.find(el => el.id === wallId);
    
    if (!wall) return null;
    
    const windowPixelWidth = unitsToPixels(width);
    const windowPixelHeight = unitsToPixels(height);
    
    return (
      <g key={id}>
        <rect
          x={position.x - windowPixelWidth / 2}
          y={position.y - wall.thickness / 2}
          width={windowPixelWidth}
          height={wall.thickness}
          fill="#87CEEB" // Bleu ciel pour les fenêtres
          stroke={isSelected ? "#007bff" : "#4682B4"}
          strokeWidth={isSelected ? 2 : 1}
          rx="0" // Coins droits
          style={{ cursor: 'pointer' }}
          onClick={(e) => {
            e.stopPropagation();
            setSelectedElement(window);
          }}
        />
        
        {/* Croisillon de fenêtre */}
        <line
          x1={position.x}
          y1={position.y - wall.thickness / 2}
          x2={position.x}
          y2={position.y + wall.thickness / 2}
          stroke="#4682B4"
          strokeWidth="1"
        />
        <line
          x1={position.x - windowPixelWidth / 2}
          y1={position.y}
          x2={position.x + windowPixelWidth / 2}
          y2={position.y}
          stroke="#4682B4"
          strokeWidth="1"
        />
        
        {isSelected && (
          <circle
            cx={position.x}
            cy={position.y}
            r="6"
            fill="#007bff"
            stroke="white"
            strokeWidth="2"
            style={{ cursor: 'move' }}
          />
        )}
      </g>
    );
  };

  const renderMeasure = (measure) => {
    const { startPoint, endPoint, measurement, id } = measure;
    const isSelected = selectedElement?.id === id;
    
    return (
      <g key={id}>
        <line
          x1={startPoint.x}
          y1={startPoint.y}
          x2={endPoint.x}
          y2={endPoint.y}
          stroke={isSelected ? "#007bff" : "#ff6600"}
          strokeWidth="2"
          strokeDasharray="5,5"
          style={{ cursor: 'pointer' }}
          onClick={(e) => {
            e.stopPropagation();
            setSelectedElement(measure);
          }}
        />
        <text
          x={(startPoint.x + endPoint.x) / 2}
          y={(startPoint.y + endPoint.y) / 2 - 15}
          textAnchor="middle"
          fontSize="14"
          fill="#ff6600"
          fontWeight="bold"
        >
          {measurement}
        </text>
        
        {/* Flèches aux extrémités */}
        <polygon
          points={`${startPoint.x},${startPoint.y} ${startPoint.x+5},${startPoint.y-3} ${startPoint.x+5},${startPoint.y+3}`}
          fill="#ff6600"
        />
        <polygon
          points={`${endPoint.x},${endPoint.y} ${endPoint.x-5},${endPoint.y-3} ${endPoint.x-5},${endPoint.y+3}`}
          fill="#ff6600"
        />
      </g>
    );
  };

  const renderGrid = () => {
    if (!showGrid) return null;
    
    const gridPixels = unitsToPixels(0.5); // Grille de 50cm
    const lines = [];
    
    for (let x = 0; x <= width; x += gridPixels) {
      lines.push(
        <line key={`v${x}`} x1={x} y1={0} x2={x} y2={height} stroke="#e0e0e0" strokeWidth="0.5" />
      );
    }
    
    for (let y = 0; y <= height; y += gridPixels) {
      lines.push(
        <line key={`h${y}`} x1={0} y1={y} x2={width} y2={y} stroke="#e0e0e0" strokeWidth="0.5" />
      );
    }
    
    return <g className="grid">{lines}</g>;
  };

  // ==================== INTERFACES ====================
  const UnitSelector = () => (
    <div className="unit-selector mb-4 p-3 bg-gray-100 rounded-lg">
      <label className="block text-sm font-medium mb-2">Unité de mesure :</label>
      <div className="flex space-x-2">
        {Object.entries(unitConversions).map(([key, unit]) => (
          <button
            key={key}
            onClick={() => setCurrentUnit(key)}
            className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${
              currentUnit === key 
                ? 'bg-blue-500 text-white' 
                : 'bg-white text-gray-700 hover:bg-gray-50'
            }`}
          >
            {unit.name} ({unit.symbol})
          </button>
        ))}
      </div>
      <div className="mt-2 text-xs text-gray-600">
        Unité courante : {unitConversions[currentUnit].name}
      </div>
    </div>
  );

  const ToolPanel = () => (
    <div className="tool-panel mb-4 p-3 bg-gray-100 rounded-lg">
      <label className="block text-sm font-medium mb-2">Outils :</label>
      <div className="grid grid-cols-3 gap-2">
        {Object.entries(tools).map(([key, tool]) => (
          <button
            key={key}
            onClick={() => setCurrentTool(key)}
            className={`p-2 rounded-md text-sm font-medium transition-colors ${
              currentTool === key 
                ? 'bg-blue-500 text-white' 
                : 'bg-white text-gray-700 hover:bg-gray-50'
            }`}
            title={tool.name}
          >
            {tool.icon} {tool.name}
          </button>
        ))}
      </div>
    </div>
  );

  const PropertiesPanel = () => (
    <div className="properties-panel p-3 bg-gray-100 rounded-lg">
      <label className="block text-sm font-medium mb-2">Propriétés :</label>
      
      <div className="space-y-3">
        <div>
          <label className="block text-xs text-gray-600 mb-1">
            Épaisseur des murs ({unitConversions[currentUnit].symbol})
          </label>
          <input
            type="range"
            min="0.1"
            max="0.5"
            step="0.05"
            value={wallThickness}
            onChange={(e) => setWallThickness(parseFloat(e.target.value))}
            className="w-full"
          />
          <div className="text-xs text-gray-500">{wallThickness.toFixed(2)}{unitConversions[currentUnit].symbol}</div>
        </div>
        
        <div>
          <label className="block text-xs text-gray-600 mb-1">
            Largeur des portes ({unitConversions[currentUnit].symbol})
          </label>
          <input
            type="range"
            min="0.6"
            max="1.2"
            step="0.1"
            value={doorWidth}
            onChange={(e) => setDoorWidth(parseFloat(e.target.value))}
            className="w-full"
          />
          <div className="text-xs text-gray-500">{doorWidth.toFixed(1)}{unitConversions[currentUnit].symbol}</div>
        </div>
        
        <div>
          <label className="block text-xs text-gray-600 mb-1">
            Largeur des fenêtres ({unitConversions[currentUnit].symbol})
          </label>
          <input
            type="range"
            min="0.6"
            max="2.0"
            step="0.1"
            value={windowWidth}
            onChange={(e) => setWindowWidth(parseFloat(e.target.value))}
            className="w-full"
          />
          <div className="text-xs text-gray-500">{windowWidth.toFixed(1)}{unitConversions[currentUnit].symbol}</div>
        </div>
        
        <div className="flex items-center space-x-2 text-xs">
          <input
            type="checkbox"
            id="showGrid"
            checked={showGrid}
            onChange={(e) => setShowGrid(e.target.checked)}
          />
          <label htmlFor="showGrid">Afficher la grille</label>
        </div>
        
        <div className="flex items-center space-x-2 text-xs">
          <input
            type="checkbox"
            id="snapToGrid"
            checked={snapToGrid}
            onChange={(e) => setSnapToGrid(e.target.checked)}
          />
          <label htmlFor="snapToGrid">Magnétisme grille</label>
        </div>
        
        <div className="flex items-center space-x-2 text-xs">
          <input
            type="checkbox"
            id="showMeasurements"
            checked={showMeasurements}
            onChange={(e) => setShowMeasurements(e.target.checked)}
          />
          <label htmlFor="showMeasurements">Afficher mesures</label>
        </div>
      </div>
      
      {selectedElement && (
        <div className="mt-4 p-2 bg-blue-50 rounded">
          <div className="text-xs font-medium text-blue-800 mb-1">Élément sélectionné :</div>
          <div className="text-xs text-blue-600">
            Type: {selectedElement.type}<br/>
            ID: {selectedElement.id.substring(0, 8)}...
          </div>
          <button
            onClick={() => {
              setElements(prev => prev.filter(el => el.id !== selectedElement.id));
              setSelectedElement(null);
            }}
            className="mt-2 px-2 py-1 bg-red-500 text-white text-xs rounded hover:bg-red-600"
          >
            🗑️ Supprimer
          </button>
        </div>
      )}
    </div>
  );

  // ==================== ÉVÉNEMENTS CLAVIER ====================
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Delete' && selectedElement) {
        setElements(prev => prev.filter(el => el.id !== selectedElement.id));
        setSelectedElement(null);
      } else if (e.key === 'Escape') {
        setSelectedElement(null);
        setCurrentTool('select');
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [selectedElement]);

  // ==================== CHARGEMENT DES DONNÉES ====================
  useEffect(() => {
    if (planData && planData.elements) {
      setElements(planData.elements);
    }
  }, [planData]);

  // ==================== EXPOSITION DE LA MÉTHODE DE SAUVEGARDE ====================
  useEffect(() => {
    if (editorRef.current) {
      editorRef.current.saveElements = () => ({
        elements,
        metadata: {
          unit: currentUnit,
          wallThickness,
          doorWidth,
          doorHeight,
          windowWidth,
          windowHeight,
          gridSize,
          timestamp: new Date().toISOString()
        }
      });
    }
  }, [elements, currentUnit, wallThickness, doorWidth, doorHeight, windowWidth, windowHeight, gridSize]);

  // ==================== RENDU PRINCIPAL ====================
  return (
    <div ref={editorRef} className="floor-plan-editor flex h-full">
      {/* Panneau latéral */}
      <div className="w-80 p-4 bg-gray-50 border-r overflow-y-auto">
        <UnitSelector />
        <ToolPanel />
        <PropertiesPanel />
      </div>
      
      {/* Zone de dessin */}
      <div className="flex-1 relative overflow-hidden bg-white" ref={containerRef}>
        <svg
          ref={svgRef}
          width="100%"
          height="100%"
          viewBox={viewBox}
          style={{ cursor: tools[currentTool]?.cursor || 'default' }}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          className="block"
        >
          {/* Grille */}
          {renderGrid()}
          
          {/* Éléments du plan */}
          {elements.map(element => {
            switch (element.type) {
              case 'wall': return renderWall(element);
              case 'door': return renderDoor(element);
              case 'window': return renderWindow(element);
              case 'measure': return renderMeasure(element);
              default: return null;
            }
          })}
          
          {/* Élément en cours de dessin */}
          {isDrawing && drawingData && (
            <g className="drawing-preview">
              {drawingData.type === 'wall' && (
                <line
                  x1={drawingData.startPoint.x}
                  y1={drawingData.startPoint.y}
                  x2={drawingData.currentPoint.x}
                  y2={drawingData.currentPoint.y}
                  stroke="#007bff"
                  strokeWidth="3"
                  strokeDasharray="5,5"
                />
              )}
              {drawingData.type === 'measure' && (
                <>
                  <line
                    x1={drawingData.startPoint.x}
                    y1={drawingData.startPoint.y}
                    x2={drawingData.currentPoint.x}
                    y2={drawingData.currentPoint.y}
                    stroke="#ff6600"
                    strokeWidth="2"
                    strokeDasharray="5,5"
                  />
                  <text
                    x={(drawingData.startPoint.x + drawingData.currentPoint.x) / 2}
                    y={(drawingData.startPoint.y + drawingData.currentPoint.y) / 2 - 10}
                    textAnchor="middle"
                    fontSize="12"
                    fill="#ff6600"
                  >
                    {formatMeasurement(Math.sqrt(
                      Math.pow(drawingData.currentPoint.x - drawingData.startPoint.x, 2) +
                      Math.pow(drawingData.currentPoint.y - drawingData.startPoint.y, 2)
                    ))}
                  </text>
                </>
              )}
            </g>
          )}
        </svg>
        
        {/* Informations de statut */}
        <div className="absolute bottom-4 left-4 bg-black bg-opacity-75 text-white px-3 py-2 rounded text-sm">
          <div>Outil actuel : {tools[currentTool]?.name}</div>
          <div>Unité : {unitConversions[currentUnit].name}</div>
          <div>Éléments : {elements.length}</div>
          {selectedElement && <div>Sélectionné : {selectedElement.type}</div>}
        </div>
      </div>
    </div>
  );
};

export default FloorPlanEditor;