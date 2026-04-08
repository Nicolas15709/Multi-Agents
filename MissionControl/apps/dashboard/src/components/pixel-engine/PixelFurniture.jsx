import React from 'react';
import { TILE_SIZE } from './constants';

const PixelFurniture = ({ furniture }) => {
  if (!furniture) return null;

  const { type, col, row, uid } = furniture;
  
  // Strip suffix like :left
  const baseType = type.split(':')[0];
  const isFlipped = type.includes(':left');

  // Define offsets and assets
  const assetPath = `/pixel-assets/furniture/${baseType}/sprite.png`;

  // We'll need the width/height to position properly if they are taller than 1 tile
  // For now, we assume standard footprints. In a real engine we'd use manifests.
  // Let's use a few common ones for now.
  const commonFurniture = {
    'TABLE_FRONT': { w: 3, h: 4 },
    'COFFEE_TABLE': { w: 2, h: 2 },
    'SOFA_BACK': { w: 4, h: 2 },
    'SOFA_FRONT': { w: 4, h: 2 },
    'SOFA_SIDE': { w: 2, h: 4 },
    'DESK_FRONT': { w: 3, h: 2 },
    'PC_FRONT_OFF': { w: 1, h: 1 },
    'PLANT': { w: 1, h: 2 },
    'BOOKSHELF': { w: 2, h: 3 },
    'DOUBLE_BOOKSHELF': { w: 4, h: 3 },
    'CLOCK': { w: 1, h: 1 },
    'BIN': { w: 1, h: 1 },
    'SMALL_PAINTING': { w: 1, h: 1 },
    'LARGE_PAINTING': { w: 2, h: 2 },
    'WOODEN_CHAIR_SIDE': { w: 1, h: 2 },
    'CUSHIONED_BENCH': { w: 2, h: 2 },
  };

  const footprint = commonFurniture[baseType] || { w: 1, h: 1 };
  
  return (
    <div 
      className="pixel-furniture"
      id={`furniture-${uid}`}
      style={{
        position: 'absolute',
        left: col * TILE_SIZE,
        top: row * TILE_SIZE,
        width: footprint.w * TILE_SIZE,
        height: footprint.h * TILE_SIZE,
        backgroundImage: `url(${assetPath})`,
        backgroundSize: '100% 100%',
        imageRendering: 'pixelated',
        transform: isFlipped ? 'scaleX(-1)' : 'none',
        zIndex: (row + footprint.h) * TILE_SIZE, // Deep sorting
        pointerEvents: 'none'
      }}
    />
  );
};

export default PixelFurniture;
