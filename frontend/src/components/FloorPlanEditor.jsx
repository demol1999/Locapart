import React, { useState, useRef, useEffect, useCallback } from 'react';

const FloorPlanEditor = ({ 
  planData = null, 
  onSave = () => {}, 
  onExport = () => {},
  width = 800, 
  height = 600,
  readonly = false 
}) => {
  // État principal de l'éditeur
  const [elements, setElements] = useState([]);
  const [selectedElement, setSelectedElement] = useState(null);
  const [currentTool, setCurrentTool] = useState('select');
  const [isDrawing, setIsDrawing] = useState(false);
  const [drawingData, setDrawingData] = useState(null);
  
  // Configuration de la grille et du zoom
  const [scale, setScale] = useState(1);
  const [panOffset, setPanOffset] = useState({ x: 0, y: 0 });
  const [gridSize, setGridSize] = useState(20);
  const [showGrid, setShowGrid] = useState(true);
  const [snapToGrid, setSnapToGrid] = useState(true);
  
  // Propriétés des éléments
  const [wallThickness, setWallThickness] = useState(10);
  const [doorWidth, setDoorWidth] = useState(80);
  const [windowWidth, setWindowWidth] = useState(120);
  
  // Références
  const svgRef = useRef(null);
  const containerRef = useRef(null);
  const editorRef = useRef(null);
  const [viewBox, setViewBox] = useState(`0 0 ${width} ${height}`);

  // Types d'outils disponibles
  const tools = {
    select: { icon: '↖️', name: 'Sélection', cursor: 'default' },
    wall: { icon: '🧱', name: 'Mur', cursor: 'crosshair' },
    door: { icon: '🚪', name: 'Porte', cursor: 'crosshair' },
    window: { icon: '🪟', name: 'Fenêtre', cursor: 'crosshair' },
    measure: { icon: '📏', name: 'Mesure', cursor: 'crosshair' },
    erase: { icon: '🗑️', name: 'Gomme', cursor: 'crosshair' }
  };

  // Fonctions utilitaires
  const snapToGridPoint = useCallback((point) => {
    if (!snapToGrid) return point;
    return {
      x: Math.round(point.x / gridSize) * gridSize,
      y: Math.round(point.y / gridSize) * gridSize
    };
  }, [snapToGrid, gridSize]);

  // Charger les données du plan si fourni
  useEffect(() => {
    if (planData && planData.elements) {
      setElements(planData.elements);
    }
  }, [planData]);

  // Exposer la méthode de sauvegarde
  useEffect(() => {
    if (editorRef.current) {
      editorRef.current.saveElements = () => elements;
    }
  }, [elements]);

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

  // Gestionnaires d'événements souris
  const handleMouseDown = useCallback((e) => {
    if (readonly) return;
    
    const point = getSVGPoint(e.clientX, e.clientY);
    
    if (currentTool === 'select') {
      // Logique de sélection
      setSelectedElement(null);
    } else if (currentTool === 'wall') {
      setIsDrawing(true);
      setDrawingData({
        startPoint: point,
        currentPoint: point,
        type: 'wall'
      });
    } else if (currentTool === 'door' || currentTool === 'window') {
      // Placement sur un mur existant
      const targetWall = findWallAtPoint(point);
      if (targetWall) {
        const newElement = {
          id: generateId(),
          type: currentTool,
          wallId: targetWall.id,
          position: projectPointOnWall(point, targetWall),
          width: currentTool === 'door' ? doorWidth : windowWidth,
          properties: {
            opening: currentTool === 'door' ? 'inward-left' : null,
            height: currentTool === 'window' ? 10 : null
          }
        };
        setElements(prev => [...prev, newElement]);
      }
    }
  }, [currentTool, readonly, getSVGPoint, doorWidth, windowWidth]);

  const handleMouseMove = useCallback((e) => {
    if (!isDrawing || readonly) return;
    
    const point = getSVGPoint(e.clientX, e.clientY);
    
    setDrawingData(prev => ({
      ...prev,
      currentPoint: point
    }));
  }, [isDrawing, readonly, getSVGPoint]);

  const handleMouseUp = useCallback((e) => {
    if (!isDrawing || readonly) return;
    
    const point = getSVGPoint(e.clientX, e.clientY);
    
    if (currentTool === 'wall' && drawingData) {
      const { startPoint } = drawingData;
      
      // Éviter les murs trop petits
      const distance = Math.sqrt(
        Math.pow(point.x - startPoint.x, 2) + Math.pow(point.y - startPoint.y, 2)
      );
      
      if (distance > 10) {
        const newWall = {
          id: generateId(),
          type: 'wall',
          startPoint,
          endPoint: point,
          thickness: wallThickness,
          properties: {}
        };
        setElements(prev => [...prev, newWall]);
      }
    }
    
    setIsDrawing(false);
    setDrawingData(null);
  }, [isDrawing, readonly, currentTool, drawingData, wallThickness, getSVGPoint]);

  // Fonctions helper pour trouver les murs
  const findWallAtPoint = (point) => {
    return elements.find(el => {
      if (el.type !== 'wall') return false;
      
      // Calcul de distance point-ligne
      const { startPoint, endPoint, thickness } = el;
      const lineLength = Math.sqrt(
        Math.pow(endPoint.x - startPoint.x, 2) + Math.pow(endPoint.y - startPoint.y, 2)
      );
      
      if (lineLength === 0) return false;
      
      const t = Math.max(0, Math.min(1, 
        ((point.x - startPoint.x) * (endPoint.x - startPoint.x) + 
         (point.y - startPoint.y) * (endPoint.y - startPoint.y)) / (lineLength * lineLength)
      ));
      
      const projection = {
        x: startPoint.x + t * (endPoint.x - startPoint.x),
        y: startPoint.y + t * (endPoint.y - startPoint.y)
      };
      
      const distance = Math.sqrt(
        Math.pow(point.x - projection.x, 2) + Math.pow(point.y - projection.y, 2)
      );
      
      return distance <= thickness / 2 + 5; // 5px de tolérance
    });
  };

  const projectPointOnWall = (point, wall) => {
    const { startPoint, endPoint } = wall;
    const lineLength = Math.sqrt(
      Math.pow(endPoint.x - startPoint.x, 2) + Math.pow(endPoint.y - startPoint.y, 2)
    );
    
    const t = Math.max(0, Math.min(1,
      ((point.x - startPoint.x) * (endPoint.x - startPoint.x) + 
       (point.y - startPoint.y) * (endPoint.y - startPoint.y)) / (lineLength * lineLength)
    ));
    
    return {
      x: startPoint.x + t * (endPoint.x - startPoint.x),
      y: startPoint.y + t * (endPoint.y - startPoint.y),
      t: t // Position relative sur le mur (0-1)
    };
  };

  // Gestionnaire de zoom
  const handleWheel = useCallback((e) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    const newScale = Math.max(0.1, Math.min(3, scale * delta));
    setScale(newScale);
  }, [scale]);

  // Rendu des éléments
  const renderGrid = () => {
    if (!showGrid) return null;
    
    const gridLines = [];
    const gridOpacity = Math.max(0.1, Math.min(0.5, scale / 2));
    
    // Lignes verticales
    for (let x = 0; x <= width; x += gridSize) {
      gridLines.push(
        <line 
          key={`v${x}`}
          x1={x} y1={0} 
          x2={x} y2={height}
          stroke="#e0e0e0" 
          strokeWidth={0.5}
          opacity={gridOpacity}
        />
      );
    }
    
    // Lignes horizontales
    for (let y = 0; y <= height; y += gridSize) {
      gridLines.push(
        <line 
          key={`h${y}`}
          x1={0} y1={y} 
          x2={width} y2={y}
          stroke="#e0e0e0" 
          strokeWidth={0.5}
          opacity={gridOpacity}
        />
      );
    }
    
    return <g id="grid">{gridLines}</g>;
  };

  const renderWall = (wall) => {
    const { startPoint, endPoint, thickness, id } = wall;
    const isSelected = selectedElement?.id === id;
    
    return (
      <g key={id}>
        <line
          x1={startPoint.x} y1={startPoint.y}
          x2={endPoint.x} y2={endPoint.y}
          stroke={isSelected ? "#ff6b6b" : "#333"}
          strokeWidth={thickness}
          strokeLinecap="round"
          onClick={() => setSelectedElement(wall)}
          style={{ cursor: 'pointer' }}
        />
        {isSelected && (
          <g>
            <circle cx={startPoint.x} cy={startPoint.y} r="4" fill="#ff6b6b" />
            <circle cx={endPoint.x} cy={endPoint.y} r="4" fill="#ff6b6b" />
          </g>
        )}
      </g>
    );
  };

  const renderDoor = (door) => {
    const wall = elements.find(el => el.id === door.wallId);
    if (!wall) return null;
    
    const { position, width, properties, id } = door;
    const isSelected = selectedElement?.id === id;
    
    // Calculer l'angle du mur
    const wallAngle = Math.atan2(
      wall.endPoint.y - wall.startPoint.y,
      wall.endPoint.x - wall.startPoint.x
    );
    
    // Décalage perpendiculaire pour l'arc d'ouverture
    const offset = wall.thickness / 2 + 2;
    const perpAngle = wallAngle + Math.PI / 2;
    
    const arcDirection = properties.opening?.includes('left') ? 1 : -1;
    const arcRadius = width * 0.8;
    
    return (
      <g key={id}>
        {/* Ouverture dans le mur */}
        <line
          x1={position.x - Math.cos(wallAngle) * width / 2}
          y1={position.y - Math.sin(wallAngle) * width / 2}
          x2={position.x + Math.cos(wallAngle) * width / 2}
          y2={position.y + Math.sin(wallAngle) * width / 2}
          stroke="white"
          strokeWidth={wall.thickness + 2}
          strokeLinecap="round"
        />
        
        {/* Arc d'ouverture */}
        <path
          d={`M ${position.x} ${position.y} 
              A ${arcRadius} ${arcRadius} 0 0 ${arcDirection > 0 ? 1 : 0} 
              ${position.x + Math.cos(wallAngle + arcDirection * Math.PI / 2) * arcRadius} 
              ${position.y + Math.sin(wallAngle + arcDirection * Math.PI / 2) * arcRadius}`}
          stroke={isSelected ? "#4ecdc4" : "#666"}
          strokeWidth="1.5"
          fill="none"
          strokeDasharray="3,3"
          onClick={() => setSelectedElement(door)}
          style={{ cursor: 'pointer' }}
        />
        
        {/* Indicateur de porte */}
        <rect
          x={position.x - 2}
          y={position.y - 2}
          width={4}
          height={4}
          fill={isSelected ? "#4ecdc4" : "#666"}
          onClick={() => setSelectedElement(door)}
          style={{ cursor: 'pointer' }}
        />
      </g>
    );
  };

  const renderWindow = (window) => {
    const wall = elements.find(el => el.id === window.wallId);
    if (!wall) return null;
    
    const { position, width, id } = window;
    const isSelected = selectedElement?.id === id;
    
    const wallAngle = Math.atan2(
      wall.endPoint.y - wall.startPoint.y,
      wall.endPoint.x - wall.startPoint.x
    );
    
    return (
      <g key={id}>
        {/* Ouverture dans le mur */}
        <line
          x1={position.x - Math.cos(wallAngle) * width / 2}
          y1={position.y - Math.sin(wallAngle) * width / 2}
          x2={position.x + Math.cos(wallAngle) * width / 2}
          y2={position.y + Math.sin(wallAngle) * width / 2}
          stroke="white"
          strokeWidth={wall.thickness + 2}
          strokeLinecap="round"
        />
        
        {/* Fenêtre */}
        <line
          x1={position.x - Math.cos(wallAngle) * width / 2}
          y1={position.y - Math.sin(wallAngle) * width / 2}
          x2={position.x + Math.cos(wallAngle) * width / 2}
          y2={position.y + Math.sin(wallAngle) * width / 2}
          stroke={isSelected ? "#51cf66" : "#4dabf7"}
          strokeWidth="3"
          strokeLinecap="round"
          onClick={() => setSelectedElement(window)}
          style={{ cursor: 'pointer' }}
        />
        
        {/* Croisillons */}
        <line
          x1={position.x - Math.cos(wallAngle) * width / 6}
          y1={position.y - Math.sin(wallAngle) * width / 6}
          x2={position.x + Math.cos(wallAngle) * width / 6}
          y2={position.y + Math.sin(wallAngle) * width / 6}
          stroke={isSelected ? "#51cf66" : "#4dabf7"}
          strokeWidth="1"
        />
      </g>
    );
  };

  const renderDrawingGuide = () => {
    if (!isDrawing || !drawingData) return null;
    
    const { startPoint, currentPoint, type } = drawingData;
    
    if (type === 'wall') {
      return (
        <g>
          <line
            x1={startPoint.x} y1={startPoint.y}
            x2={currentPoint.x} y2={currentPoint.y}
            stroke="#ff6b6b"
            strokeWidth={wallThickness}
            strokeLinecap="round"
            opacity="0.6"
            strokeDasharray="5,5"
          />
          {/* Afficher la longueur */}
          <text
            x={(startPoint.x + currentPoint.x) / 2}
            y={(startPoint.y + currentPoint.y) / 2 - 10}
            fill="#333"
            fontSize="12"
            textAnchor="middle"
          >
            {Math.round(Math.sqrt(
              Math.pow(currentPoint.x - startPoint.x, 2) + 
              Math.pow(currentPoint.y - startPoint.y, 2)
            ))} px
          </text>
        </g>
      );
    }
    
    return null;
  };

  return (
    <div ref={editorRef} className="flex flex-col h-full bg-gray-50" data-floor-plan-editor>
      {/* Barre d'outils */}
      <div className="flex items-center justify-between p-4 bg-white border-b shadow-sm">
        <div className="flex items-center space-x-2">
          {Object.entries(tools).map(([toolKey, tool]) => (
            <button
              key={toolKey}
              onClick={() => setCurrentTool(toolKey)}
              className={`p-2 rounded-md transition-colors ${
                currentTool === toolKey 
                  ? 'bg-indigo-100 text-indigo-700 border-indigo-300' 
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              } border`}
              title={tool.name}
            >
              <span className="text-lg">{tool.icon}</span>
            </button>
          ))}
        </div>
        
        <div className="flex items-center space-x-4">
          <label className="flex items-center space-x-2">
            <input
              type="checkbox"
              checked={showGrid}
              onChange={(e) => setShowGrid(e.target.checked)}
              className="rounded"
            />
            <span className="text-sm">Grille</span>
          </label>
          
          <label className="flex items-center space-x-2">
            <input
              type="checkbox"
              checked={snapToGrid}
              onChange={(e) => setSnapToGrid(e.target.checked)}
              className="rounded"
            />
            <span className="text-sm">Aimant</span>
          </label>
          
          <span className="text-sm text-gray-600">
            Zoom: {Math.round(scale * 100)}%
          </span>
        </div>
      </div>

      {/* Zone d'édition */}
      <div className="flex flex-1">
        {/* Panneau de propriétés */}
        <div className="w-64 bg-white border-r p-4 space-y-4">
          <h3 className="font-medium text-gray-900">Propriétés</h3>
          
          {currentTool === 'wall' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Épaisseur du mur
              </label>
              <input
                type="range"
                min="5"
                max="30"
                value={wallThickness}
                onChange={(e) => setWallThickness(parseInt(e.target.value))}
                className="w-full"
              />
              <span className="text-sm text-gray-600">{wallThickness}px</span>
            </div>
          )}
          
          {currentTool === 'door' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Largeur de la porte
              </label>
              <input
                type="range"
                min="60"
                max="120"
                value={doorWidth}
                onChange={(e) => setDoorWidth(parseInt(e.target.value))}
                className="w-full"
              />
              <span className="text-sm text-gray-600">{doorWidth}px</span>
            </div>
          )}
          
          {currentTool === 'window' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Largeur de la fenêtre
              </label>
              <input
                type="range"
                min="80"
                max="200"
                value={windowWidth}
                onChange={(e) => setWindowWidth(parseInt(e.target.value))}
                className="w-full"
              />
              <span className="text-sm text-gray-600">{windowWidth}px</span>
            </div>
          )}
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Taille de la grille
            </label>
            <input
              type="range"
              min="10"
              max="50"
              value={gridSize}
              onChange={(e) => setGridSize(parseInt(e.target.value))}
              className="w-full"
            />
            <span className="text-sm text-gray-600">{gridSize}px</span>
          </div>
          
          {selectedElement && (
            <div className="pt-4 border-t">
              <h4 className="font-medium text-gray-900 mb-2">Élément sélectionné</h4>
              <p className="text-sm text-gray-600">
                Type: {selectedElement.type}
              </p>
              <button
                onClick={() => {
                  setElements(prev => prev.filter(el => el.id !== selectedElement.id));
                  setSelectedElement(null);
                }}
                className="mt-2 w-full bg-red-600 text-white py-1 px-2 rounded text-sm hover:bg-red-700"
              >
                Supprimer
              </button>
            </div>
          )}
        </div>

        {/* Canvas principal */}
        <div 
          ref={containerRef}
          className="flex-1 overflow-hidden"
          style={{ cursor: tools[currentTool]?.cursor || 'default' }}
        >
          <svg
            ref={svgRef}
            width="100%"
            height="100%"
            viewBox={viewBox}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onWheel={handleWheel}
            className="bg-white"
          >
            {renderGrid()}
            
            {/* Rendu des éléments */}
            {elements.map(element => {
              if (element.type === 'wall') return renderWall(element);
              if (element.type === 'door') return renderDoor(element);
              if (element.type === 'window') return renderWindow(element);
              return null;
            })}
            
            {renderDrawingGuide()}
          </svg>
        </div>
      </div>

      {/* Barre de statut */}
      <div className="p-2 bg-gray-100 border-t text-sm text-gray-600 flex items-center justify-between">
        <span>
          Éléments: {elements.length} | 
          Murs: {elements.filter(e => e.type === 'wall').length} | 
          Ouvertures: {elements.filter(e => e.type === 'door' || e.type === 'window').length}
        </span>
        <span>
          Outil actuel: {tools[currentTool]?.name}
        </span>
      </div>
    </div>
  );
};

export default FloorPlanEditor;