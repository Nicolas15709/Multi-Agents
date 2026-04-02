import { Direction, TILE_SIZE } from '../types.js'
import type { SpriteData, TileType as TileTypeVal, Character, PetTypeValue } from '../types.js'
import { findPath } from '../layout/tileMap.js'
import { CAT_SPRITES } from '../sprites/petSprites.js'
import type { PetSprites } from '../sprites/petSprites.js'
import { DOG_SPRITES } from '../sprites/dogSprites.js'
import {
  PET_WALK_SPEED_PX_PER_SEC,
  PET_WANDER_PAUSE_MIN_SEC,
  PET_WANDER_PAUSE_MAX_SEC,
  PET_SLEEP_DURATION_MIN_SEC,
  PET_SLEEP_DURATION_MAX_SEC,
  PET_SIT_DURATION_MIN_SEC,
  PET_SIT_DURATION_MAX_SEC,
  PET_WALK_FRAME_DURATION_SEC,
} from '../../constants.js'

const PetState = {
  IDLE: 'idle',
  WALK: 'walk',
  SIT: 'sit',
  SLEEP: 'sleep',
  SCARED: 'scared',
} as const
type PetStateType = (typeof PetState)[keyof typeof PetState]

export interface Pet {
  id: number
  configId: string
  name: string
  state: PetStateType
  dir: Direction
  x: number
  y: number
  tileCol: number
  tileRow: number
  path: Array<{ col: number; row: number }>
  moveProgress: number
  frame: number
  frameTimer: number
  stateTimer: number
  sprites: PetSprites
}

let nextPetId = 1

function spritesForType(type: PetTypeValue | undefined): PetSprites {
  return type === 'dog' ? DOG_SPRITES : CAT_SPRITES
}

export function createPet(col: number, row: number, configId: string, name: string, type?: PetTypeValue): Pet {
  return {
    id: nextPetId++,
    configId,
    name,
    state: PetState.IDLE,
    dir: Direction.DOWN,
    x: col * TILE_SIZE + TILE_SIZE / 2,
    y: row * TILE_SIZE + TILE_SIZE / 2,
    tileCol: col,
    tileRow: row,
    path: [],
    moveProgress: 0,
    frame: 0,
    frameTimer: 0,
    stateTimer: randomRange(PET_WANDER_PAUSE_MIN_SEC, PET_WANDER_PAUSE_MAX_SEC),
    sprites: spritesForType(type),
  }
}

/** Update a pet's name and/or type (for live editing in settings) */
export function updatePetConfig(pet: Pet, name: string, type?: PetTypeValue): void {
  pet.name = name
  const newSprites = spritesForType(type)
  if (pet.sprites !== newSprites) {
    pet.sprites = newSprites
    pet.frame = 0
    pet.frameTimer = 0
  }
}

function tileCenter(col: number, row: number): { x: number; y: number } {
  return {
    x: col * TILE_SIZE + TILE_SIZE / 2,
    y: row * TILE_SIZE + TILE_SIZE / 2,
  }
}

function dirBetween(fromCol: number, fromRow: number, toCol: number, toRow: number): Direction {
  const dc = toCol - fromCol
  const dr = toRow - fromRow
  if (dc > 0) return Direction.RIGHT
  if (dc < 0) return Direction.LEFT
  if (dr > 0) return Direction.DOWN
  return Direction.UP
}

export function updatePet(
  pet: Pet,
  dt: number,
  walkableTiles: Array<{ col: number; row: number }>,
  tileMap: TileTypeVal[][],
  blockedTiles: Set<string>,
  characters: Map<number, Character>,
): void {
  pet.frameTimer += dt

  switch (pet.state) {
    case PetState.IDLE: {
      // Cycle idle frames (tail wagging animation)
      if (pet.frameTimer >= PET_WALK_FRAME_DURATION_SEC) {
        pet.frameTimer -= PET_WALK_FRAME_DURATION_SEC
        pet.frame = (pet.frame + 1) % pet.sprites.idle.length
      }
      pet.stateTimer -= dt
      if (pet.stateTimer <= 0) {
        // Decide next behavior
        const roll = Math.random()
        if (roll < 0.4) {
          // Wander to random tile
          tryWander(pet, walkableTiles, tileMap, blockedTiles)
        } else if (roll < 0.7) {
          // Approach idle agent
          const idleAgent = findIdleAgent(pet, characters)
          if (idleAgent) {
            const path = findPath(pet.tileCol, pet.tileRow, idleAgent.tileCol, idleAgent.tileRow, tileMap, blockedTiles)
            if (path.length > 1) {
              // Walk to tile near agent (not exactly on agent)
              path.pop()
              pet.path = path
              pet.moveProgress = 0
              pet.state = PetState.WALK
              pet.frame = 0
              pet.frameTimer = 0
            } else {
              // Already near agent, sit
              pet.state = PetState.SIT
              pet.stateTimer = randomRange(PET_SIT_DURATION_MIN_SEC, PET_SIT_DURATION_MAX_SEC)
              pet.frame = 0
              pet.frameTimer = 0
            }
          } else {
            tryWander(pet, walkableTiles, tileMap, blockedTiles)
          }
        } else if (roll < 0.9) {
          // Sleep
          pet.state = PetState.SLEEP
          pet.stateTimer = randomRange(PET_SLEEP_DURATION_MIN_SEC, PET_SLEEP_DURATION_MAX_SEC)
          pet.frame = 0
          pet.frameTimer = 0
        } else {
          // Flee from active agent (scared)
          const activeAgent = findActiveAgent(pet, characters)
          if (activeAgent) {
            const awayCol = pet.tileCol + (pet.tileCol - activeAgent.tileCol)
            const awayRow = pet.tileRow + (pet.tileRow - activeAgent.tileRow)
            const target = findNearestWalkable(awayCol, awayRow, walkableTiles)
            if (target) {
              const path = findPath(pet.tileCol, pet.tileRow, target.col, target.row, tileMap, blockedTiles)
              if (path.length > 0) {
                pet.path = path
                pet.moveProgress = 0
                pet.state = PetState.SCARED
                pet.frame = 0
                pet.frameTimer = 0
              }
            }
          }
          if (pet.state === PetState.IDLE) {
            tryWander(pet, walkableTiles, tileMap, blockedTiles)
          }
        }
        if (pet.state === PetState.IDLE) {
          pet.stateTimer = randomRange(PET_WANDER_PAUSE_MIN_SEC, PET_WANDER_PAUSE_MAX_SEC)
        }
      }
      break
    }

    case PetState.WALK:
    case PetState.SCARED: {
      const frameCount = pet.state === PetState.SCARED
        ? pet.sprites.scared.length
        : pet.sprites.walk.length
      if (pet.frameTimer >= PET_WALK_FRAME_DURATION_SEC) {
        pet.frameTimer -= PET_WALK_FRAME_DURATION_SEC
        pet.frame = (pet.frame + 1) % frameCount
      }

      if (pet.path.length === 0) {
        const center = tileCenter(pet.tileCol, pet.tileRow)
        pet.x = center.x
        pet.y = center.y
        pet.state = PetState.IDLE
        pet.stateTimer = randomRange(PET_WANDER_PAUSE_MIN_SEC, PET_WANDER_PAUSE_MAX_SEC)
        pet.frame = 0
        pet.frameTimer = 0
        break
      }

      const next = pet.path[0]
      pet.dir = dirBetween(pet.tileCol, pet.tileRow, next.col, next.row)
      pet.moveProgress += (PET_WALK_SPEED_PX_PER_SEC / TILE_SIZE) * dt

      const from = tileCenter(pet.tileCol, pet.tileRow)
      const to = tileCenter(next.col, next.row)
      const t = Math.min(pet.moveProgress, 1)
      pet.x = from.x + (to.x - from.x) * t
      pet.y = from.y + (to.y - from.y) * t

      if (pet.moveProgress >= 1) {
        pet.tileCol = next.col
        pet.tileRow = next.row
        pet.x = to.x
        pet.y = to.y
        pet.path.shift()
        pet.moveProgress = 0
      }
      break
    }

    case PetState.SIT: {
      // Cycle idle frames while sitting (same animation as idle)
      if (pet.frameTimer >= PET_WALK_FRAME_DURATION_SEC) {
        pet.frameTimer -= PET_WALK_FRAME_DURATION_SEC
        pet.frame = (pet.frame + 1) % pet.sprites.idle.length
      }
      pet.stateTimer -= dt
      if (pet.stateTimer <= 0) {
        pet.state = PetState.IDLE
        pet.stateTimer = randomRange(PET_WANDER_PAUSE_MIN_SEC, PET_WANDER_PAUSE_MAX_SEC)
        pet.frame = 0
        pet.frameTimer = 0
      }
      break
    }

    case PetState.SLEEP: {
      // Cycle sleep frames
      if (pet.frameTimer >= PET_WALK_FRAME_DURATION_SEC) {
        pet.frameTimer -= PET_WALK_FRAME_DURATION_SEC
        pet.frame = (pet.frame + 1) % pet.sprites.sleep.length
      }
      pet.stateTimer -= dt
      if (pet.stateTimer <= 0) {
        pet.state = PetState.IDLE
        pet.stateTimer = randomRange(PET_WANDER_PAUSE_MIN_SEC, PET_WANDER_PAUSE_MAX_SEC)
        pet.frame = 0
        pet.frameTimer = 0
      }
      break
    }
  }
}

export function getPetSprite(pet: Pet): SpriteData {
  if (pet.state === 'sleep') return pet.sprites.sleep[pet.frame % pet.sprites.sleep.length]
  if (pet.state === 'scared') return pet.sprites.scared[pet.frame % pet.sprites.scared.length]
  if (pet.state === 'walk') {
    // Use directional sprites if available
    const dirSprites = getDirectionalWalkSprites(pet)
    if (dirSprites) return dirSprites[pet.frame % dirSprites.length]
    return pet.sprites.walk[pet.frame % pet.sprites.walk.length]
  }
  // idle and sit use idle animation
  return pet.sprites.idle[pet.frame % pet.sprites.idle.length]
}

function getDirectionalWalkSprites(pet: Pet): SpriteData[] | undefined {
  switch (pet.dir) {
    case Direction.DOWN: return pet.sprites.walkDown
    case Direction.UP: return pet.sprites.walkUp
    case Direction.LEFT: return pet.sprites.walkLeft
    case Direction.RIGHT: return pet.sprites.walkRight
    default: return undefined
  }
}

export function isPetFacingLeft(pet: Pet): boolean {
  // If directional walk sprites exist, don't flip during walk (sprites already face correct direction)
  if (pet.state === 'walk' && pet.sprites.walkLeft) {
    return false
  }
  // Only flip horizontally during walk/scared (side-view sprites)
  // Idle and sleep are front-view, no flip needed
  if (pet.state === 'walk' || pet.state === 'scared') {
    return pet.dir === Direction.LEFT
  }
  return false
}

function tryWander(
  pet: Pet,
  walkableTiles: Array<{ col: number; row: number }>,
  tileMap: TileTypeVal[][],
  blockedTiles: Set<string>,
): void {
  if (walkableTiles.length === 0) return
  const target = walkableTiles[Math.floor(Math.random() * walkableTiles.length)]
  const path = findPath(pet.tileCol, pet.tileRow, target.col, target.row, tileMap, blockedTiles)
  if (path.length > 0) {
    // Limit path length so pet doesn't walk across the entire map
    pet.path = path.slice(0, 6)
    pet.moveProgress = 0
    pet.state = 'walk' as PetStateType
    pet.frame = 0
    pet.frameTimer = 0
  }
}

function findIdleAgent(pet: Pet, characters: Map<number, Character>): Character | null {
  let closest: Character | null = null
  let bestDist = Infinity
  for (const ch of characters.values()) {
    if (ch.isActive || ch.isSubagent) continue
    const d = Math.abs(ch.tileCol - pet.tileCol) + Math.abs(ch.tileRow - pet.tileRow)
    if (d < bestDist) {
      bestDist = d
      closest = ch
    }
  }
  return closest
}

function findActiveAgent(pet: Pet, characters: Map<number, Character>): Character | null {
  let closest: Character | null = null
  let bestDist = Infinity
  for (const ch of characters.values()) {
    if (!ch.isActive || ch.isSubagent) continue
    const d = Math.abs(ch.tileCol - pet.tileCol) + Math.abs(ch.tileRow - pet.tileRow)
    if (d < bestDist && d <= 3) {
      bestDist = d
      closest = ch
    }
  }
  return closest
}

function findNearestWalkable(col: number, row: number, walkableTiles: Array<{ col: number; row: number }>): { col: number; row: number } | null {
  if (walkableTiles.length === 0) return null
  let best = walkableTiles[0]
  let bestDist = Math.abs(best.col - col) + Math.abs(best.row - row)
  for (let i = 1; i < walkableTiles.length; i++) {
    const d = Math.abs(walkableTiles[i].col - col) + Math.abs(walkableTiles[i].row - row)
    if (d < bestDist) {
      bestDist = d
      best = walkableTiles[i]
    }
  }
  return best
}

function randomRange(min: number, max: number): number {
  return min + Math.random() * (max - min)
}
