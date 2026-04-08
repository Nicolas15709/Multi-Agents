import React, { useEffect, useState } from 'react';

// Character PNG dimensions: 112x96
// Frames are 16x32 pixels
// 3 Rows: 0 = Down, 32 = Up, 64 = Right
// Columns (16px per step):
// 0, 1, 2 = Walk Cycle
// 3, 4 = Typing
// 5, 6 = Reading

const DIRECTION_MAP = {
  down: 0,
  up: 1,
  right: 2,
  left: 2, // We'll CSS scaleX(-1) for left
};

const ANIMATION_FRAMES = {
  idle: [1], // Default frame
  walk: [0, 1, 2, 1], // 4 frame cycle
  type: [3, 4], // 2 frame cycle
  read: [5, 6], // 2 frame cycle
};

export const PixelAgent = ({
  x = 0,
  y = 0,
  agentId = 'agent-0',
  charIndex = 0,
  direction = 'down', // down, up, right, left
  state = 'idle', // idle, walk, type, read
  scale = 2,
}) => {
  const [frameIndex, setFrameIndex] = useState(0);

  useEffect(() => {
    // Basic CSS animation loop matching the pixel-agents 16-bit retro feel
    const frames = ANIMATION_FRAMES[state] || ANIMATION_FRAMES.idle;
    // Walk is faster, Type/Read is slower
    const intervalMs = state === 'walk' ? 150 : 400;

    const timer = setInterval(() => {
      setFrameIndex((prev) => (prev + 1) % frames.length);
    }, intervalMs);

    return () => clearInterval(timer);
  }, [state]);

  const yPos = DIRECTION_MAP[direction] * 32;
  const frames = ANIMATION_FRAMES[state] || ANIMATION_FRAMES.idle;
  
  // Guard against out-of-bounds frame index during state transitions
  const safeFrameIndex = frameIndex % frames.length;
  const currentFrame = frames[safeFrameIndex];
  const xPos = currentFrame * 16;
  
  // Need to render "left" by flipping the container horizontally
  const isLeft = direction === 'left';

  return (
    <div
      style={{
        position: 'absolute',
        width: 16 * scale,
        height: 32 * scale,
        // Anchor at bottom center, character's feet
        transformOrigin: 'bottom center',
        transform: `translate(${x}px, ${y}px)`,
        transition: 'transform 1.5s linear',
        zIndex: Math.round(y), // Sort by Y coordinates
        pointerEvents: 'none', // Don't block clicking
      }}
    >
      <div 
        style={{
          width: '100%',
          height: '100%',
          backgroundImage: `url('/pixel-assets/characters/char_${charIndex % 6}.png')`,
          backgroundPosition: `-${xPos * scale}px -${yPos * scale}px`,
          backgroundSize: `${112 * scale}px ${96 * scale}px`,
          imageRendering: 'pixelated', // Crucial for retro look
          transform: isLeft ? `scaleX(-1)` : 'scaleX(1)',
          transition: 'transform 0.1s', // fast flip
        }}
      />
    </div>
  );
};
