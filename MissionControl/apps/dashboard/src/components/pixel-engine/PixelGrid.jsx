import React from 'react';
import { TILE_SIZE } from './constants';

const PixelGrid = ({ layout }) => {
  if (!layout || !layout.tiles) return null;

  const { cols, rows, tiles } = layout;

  return (
    <div 
      className="pixel-grid"
      style={{
        display: 'grid',
        gridTemplateColumns: `repeat(${cols}, ${TILE_SIZE}px)`,
        gridTemplateRows: `repeat(${rows}, ${TILE_SIZE}px)`,
        width: cols * TILE_SIZE,
        height: rows * TILE_SIZE,
        position: 'absolute',
        top: 0,
        left: 0,
        pointerEvents: 'none'
      }}
    >
      {tiles.map((tileType, index) => {
        const col = index % cols;
        const row = Math.floor(index / cols);
        
        // 255 is Void
        if (tileType === 255) return <div key={index} style={{ width: TILE_SIZE, height: TILE_SIZE }} />;

        // Custom styling for floor patterns
        let backgroundColor = 'transparent';
        let backgroundImage = 'none';

        if (tileType === 0) {
          // Wall - we'll handle autotiling later or use a simple color
          backgroundColor = '#3A3A5C';
        } else if (tileType >= 1 && tileType <= 9) {
          // Floor tiles 1-9
          backgroundImage = `url(/pixel-assets/floors/floor_${tileType}.png)`;
        }

        return (
          <div 
            key={index}
            style={{
              width: TILE_SIZE,
              height: TILE_SIZE,
              backgroundColor,
              backgroundImage,
              backgroundSize: 'contain',
              imageRendering: 'pixelated'
            }}
          />
        );
      })}
    </div>
  );
};

export default PixelGrid;
