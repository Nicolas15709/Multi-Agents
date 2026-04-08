import {
  DEFAULT_COLS,
  DEFAULT_ROWS,
  Direction,
  FurnitureType,
  TILE_SIZE,
  TileType,
} from '../types.js'
import { AUTO_ON_FACING_DEPTH } from '../../constants.js'
import type {
  FloorColor,
  FurnitureInstance,
  OfficeLayout,
  PlacedFurniture,
  Seat,
  TileType as TileTypeVal,
} from '../types.js'
import { getColorizedSprite } from '../colorize.js'
import {
  getCatalogEntry,
  getEffectiveCatalogEntry,
  getOrientationInGroup,
} from './furnitureCatalog.js'

export function layoutToTileMap(layout: OfficeLayout): TileTypeVal[][] {
  const map: TileTypeVal[][] = []
  for (let row = 0; row < layout.rows; row++) {
    const tileRow: TileTypeVal[] = []
    for (let col = 0; col < layout.cols; col++) {
      tileRow.push(layout.tiles[row * layout.cols + col])
    }
    map.push(tileRow)
  }
  return map
}

export function layoutToFurnitureInstances(
  furniture: PlacedFurniture[],
  tiles?: TileTypeVal[],
  cols?: number,
): FurnitureInstance[] {
  const deskZByTile = new Map<string, number>()
  for (const item of furniture) {
    const entry = getCatalogEntry(item.type)
    if (!entry || !entry.isDesk) continue
    const deskZY = item.row * TILE_SIZE + entry.sprite.length
    for (let dr = 0; dr < entry.footprintH; dr++) {
      for (let dc = 0; dc < entry.footprintW; dc++) {
        const key = `${item.col + dc},${item.row + dr}`
        const prev = deskZByTile.get(key)
        if (prev === undefined || deskZY > prev) deskZByTile.set(key, deskZY)
      }
    }
  }

  const instances: FurnitureInstance[] = []
  for (const item of furniture) {
    const entry =
      item.type === FurnitureType.PIXEL_TEXT
        ? getEffectiveCatalogEntry(item.type, item.textConfig)
        : getCatalogEntry(item.type)
    if (!entry) continue

    const x = item.col * TILE_SIZE
    const y = item.row * TILE_SIZE
    const spriteH = entry.sprite.length
    let zY = y + spriteH

    if (entry.category === 'chairs') {
      if (entry.orientation === 'back') {
        zY = (item.row + entry.footprintH) * TILE_SIZE + 1
      } else {
        zY = (item.row + 1) * TILE_SIZE
      }
    }

    if (entry.canPlaceOnSurfaces) {
      for (let dr = 0; dr < entry.footprintH; dr++) {
        for (let dc = 0; dc < entry.footprintW; dc++) {
          const deskZ = deskZByTile.get(`${item.col + dc},${item.row + dr}`)
          if (deskZ !== undefined && deskZ + 0.5 > zY) zY = deskZ + 0.5
        }
      }
    }

    if (entry.canPlaceOnWalls && tiles && cols) {
      const bottomRow = item.row + entry.footprintH - 1
      let lowestWallRow = bottomRow
      for (let row = bottomRow; row < tiles.length / cols; row++) {
        let hasWall = false
        for (let dc = 0; dc < entry.footprintW; dc++) {
          const idx = row * cols + (item.col + dc)
          if (idx >= 0 && idx < tiles.length && tiles[idx] === TileType.WALL) {
            hasWall = true
            break
          }
        }
        if (hasWall) lowestWallRow = row
        else break
      }
      zY = (lowestWallRow + 1) * TILE_SIZE + 0.5
    }

    if (item.zLayer && item.zLayer > 0 && tiles && cols) {
      const bottomRow = item.row + entry.footprintH - 1
      let lowestWallRow = bottomRow
      for (let row = bottomRow; row < tiles.length / cols; row++) {
        let hasWall = false
        for (let dc = 0; dc < entry.footprintW; dc++) {
          const idx = row * cols + (item.col + dc)
          if (idx >= 0 && idx < tiles.length && tiles[idx] === TileType.WALL) {
            hasWall = true
            break
          }
        }
        if (hasWall) lowestWallRow = row
        else break
      }
      const wallZY = (lowestWallRow + 1) * TILE_SIZE + 0.5
      zY = Math.max(zY, wallZY)
    }

    let sprite = entry.sprite
    if (item.color && item.type !== FurnitureType.PIXEL_TEXT) {
      const { h, s, b: brightness, c: contrast } = item.color
      sprite = getColorizedSprite(
        `furn-${item.type}-${h}-${s}-${brightness}-${contrast}-${item.color.colorize ? 1 : 0}`,
        entry.sprite,
        item.color,
      )
    }

    let mirrored = false
    if (entry.mirrorSide) {
      const orientation = getOrientationInGroup(item.type)
      if (orientation === 'left') mirrored = true
    }

    instances.push({ sprite, x, y, zY, ...(mirrored ? { mirrored: true } : {}) })
  }

  return instances
}

export function getBlockedTiles(
  furniture: PlacedFurniture[],
  excludeTiles?: Set<string>,
): Set<string> {
  const tiles = new Set<string>()
  for (const item of furniture) {
    const entry =
      item.type === FurnitureType.PIXEL_TEXT
        ? getEffectiveCatalogEntry(item.type, item.textConfig)
        : getCatalogEntry(item.type)
    if (!entry) continue
    const bgRows = entry.backgroundTiles || 0
    for (let dr = 0; dr < entry.footprintH; dr++) {
      if (dr < bgRows) continue
      for (let dc = 0; dc < entry.footprintW; dc++) {
        const key = `${item.col + dc},${item.row + dr}`
        if (excludeTiles && excludeTiles.has(key)) continue
        tiles.add(key)
      }
    }
  }
  return tiles
}

export function getPlacementBlockedTiles(
  furniture: PlacedFurniture[],
  excludeUid?: string,
): Set<string> {
  const tiles = new Set<string>()
  for (const item of furniture) {
    if (item.uid === excludeUid) continue
    const entry =
      item.type === FurnitureType.PIXEL_TEXT
        ? getEffectiveCatalogEntry(item.type, item.textConfig)
        : getCatalogEntry(item.type)
    if (!entry) continue
    const bgRows = entry.backgroundTiles || 0
    for (let dr = 0; dr < entry.footprintH; dr++) {
      if (dr < bgRows) continue
      for (let dc = 0; dc < entry.footprintW; dc++) {
        tiles.add(`${item.col + dc},${item.row + dr}`)
      }
    }
  }
  return tiles
}

function orientationToFacing(orientation: string): Direction {
  switch (orientation) {
    case 'front':
      return Direction.DOWN
    case 'back':
      return Direction.UP
    case 'left':
      return Direction.LEFT
    case 'right':
    case 'side':
      return Direction.RIGHT
    default:
      return Direction.DOWN
  }
}

function seatFacesElectronics(
  seatCol: number,
  seatRow: number,
  facingDir: Direction,
  electronicsTiles: Set<string>,
): boolean {
  const dCol =
    facingDir === Direction.RIGHT ? 1 : facingDir === Direction.LEFT ? -1 : 0
  const dRow =
    facingDir === Direction.DOWN ? 1 : facingDir === Direction.UP ? -1 : 0

  for (let depth = 1; depth <= AUTO_ON_FACING_DEPTH; depth++) {
    const tileCol = seatCol + dCol * depth
    const tileRow = seatRow + dRow * depth
    if (electronicsTiles.has(`${tileCol},${tileRow}`)) return true

    if (dCol !== 0) {
      if (
        electronicsTiles.has(`${tileCol},${tileRow - 1}`) ||
        electronicsTiles.has(`${tileCol},${tileRow + 1}`)
      ) {
        return true
      }
    } else if (
      electronicsTiles.has(`${tileCol - 1},${tileRow}`) ||
      electronicsTiles.has(`${tileCol + 1},${tileRow}`)
    ) {
      return true
    }
  }

  return false
}

export function layoutToSeats(furniture: PlacedFurniture[]): Map<string, Seat> {
  const seats = new Map<string, Seat>()
  const deskTiles = new Set<string>()
  const electronicsTiles = new Set<string>()

  for (const item of furniture) {
    const entry = getCatalogEntry(item.type)
    if (!entry || !entry.isDesk) continue
    for (let dr = 0; dr < entry.footprintH; dr++) {
      for (let dc = 0; dc < entry.footprintW; dc++) {
        deskTiles.add(`${item.col + dc},${item.row + dr}`)
      }
    }
  }

  for (const item of furniture) {
    const entry = getCatalogEntry(item.type)
    if (!entry || entry.category !== 'electronics') continue
    for (let dr = 0; dr < entry.footprintH; dr++) {
      for (let dc = 0; dc < entry.footprintW; dc++) {
        electronicsTiles.add(`${item.col + dc},${item.row + dr}`)
      }
    }
  }

  const dirs: Array<{ dc: number; dr: number; facing: Direction }> = [
    { dc: 0, dr: -1, facing: Direction.UP },
    { dc: 0, dr: 1, facing: Direction.DOWN },
    { dc: -1, dr: 0, facing: Direction.LEFT },
    { dc: 1, dr: 0, facing: Direction.RIGHT },
  ]

  for (const item of furniture) {
    const entry = getCatalogEntry(item.type)
    if (!entry || entry.category !== 'chairs') continue

    let seatCount = 0
    const bgRows = entry.backgroundTiles ?? 0
    for (let dr = bgRows; dr < entry.footprintH; dr++) {
      for (let dc = 0; dc < entry.footprintW; dc++) {
        const tileCol = item.col + dc
        const tileRow = item.row + dr

        let facingDir: Direction = Direction.DOWN
        if (entry.orientation) {
          facingDir = orientationToFacing(entry.orientation)
        } else {
          for (const dir of dirs) {
            if (deskTiles.has(`${tileCol + dir.dc},${tileRow + dir.dr}`)) {
              facingDir = dir.facing
              break
            }
          }
        }

        // Only workstation chairs become assignable seats.
        if (!seatFacesElectronics(tileCol, tileRow, facingDir, electronicsTiles)) {
          continue
        }

        const seatUid = seatCount === 0 ? item.uid : `${item.uid}:${seatCount}`
        seats.set(seatUid, {
          uid: seatUid,
          seatCol: tileCol,
          seatRow: tileRow,
          facingDir,
          assigned: false,
        })
        seatCount++
      }
    }
  }

  return seats
}

export function getSeatTiles(seats: Map<string, Seat>): Set<string> {
  const tiles = new Set<string>()
  for (const seat of seats.values()) {
    tiles.add(`${seat.seatCol},${seat.seatRow}`)
  }
  return tiles
}

const DEFAULT_LEFT_ROOM_COLOR: FloorColor = { h: 35, s: 30, b: 15, c: 0 }
const DEFAULT_RIGHT_ROOM_COLOR: FloorColor = { h: 25, s: 45, b: 5, c: 10 }

export function createDefaultLayout(): OfficeLayout {
  const tiles: TileTypeVal[] = []
  const tileColors: Array<FloorColor | null> = []

  for (let row = 0; row < DEFAULT_ROWS; row++) {
    for (let col = 0; col < DEFAULT_COLS; col++) {
      if (row === 0 || row === DEFAULT_ROWS - 1 || col === 0 || col === DEFAULT_COLS - 1) {
        tiles.push(TileType.WALL)
        tileColors.push(null)
      } else if (col < Math.floor(DEFAULT_COLS / 2)) {
        tiles.push(TileType.FLOOR_1)
        tileColors.push(DEFAULT_LEFT_ROOM_COLOR)
      } else {
        tiles.push(TileType.FLOOR_2)
        tileColors.push(DEFAULT_RIGHT_ROOM_COLOR)
      }
    }
  }

  return { version: 1, cols: DEFAULT_COLS, rows: DEFAULT_ROWS, tiles, tileColors, furniture: [] }
}

export function serializeLayout(layout: OfficeLayout): string {
  return JSON.stringify(layout)
}

const LEGACY_TYPE_MAP: Record<string, string | null> = {
  desk: 'DESK_FRONT',
  chair: 'WOODEN_CHAIR_FRONT',
  bookshelf: 'BOOKSHELF',
  plant: 'PLANT',
  cooler: null,
  whiteboard: 'WHITEBOARD',
  pc: 'PC_FRONT_OFF',
  lamp: null,
}

function migrateFurnitureTypes(furniture: PlacedFurniture[]): PlacedFurniture[] {
  const migrated: PlacedFurniture[] = []
  for (const item of furniture) {
    const newType = LEGACY_TYPE_MAP[item.type]
    if (newType === undefined) {
      migrated.push(item)
    } else if (newType !== null) {
      migrated.push({ ...item, type: newType })
    }
  }
  return migrated
}

export function deserializeLayout(json: string): OfficeLayout | null {
  try {
    const obj = JSON.parse(json)
    if (obj && obj.version === 1 && Array.isArray(obj.tiles) && Array.isArray(obj.furniture)) {
      return migrateLayout(obj as OfficeLayout)
    }
  } catch {
    // Ignore parse errors.
  }
  return null
}

export function migrateLayoutColors(layout: OfficeLayout): OfficeLayout {
  return migrateLayout(layout)
}

function migrateLayout(layout: OfficeLayout): OfficeLayout {
  layout = { ...layout, furniture: migrateFurnitureTypes(layout.furniture) }

  const oldVoid = 8
  if (!layout.layoutRevision && layout.tiles.includes(oldVoid as TileTypeVal)) {
    layout = {
      ...layout,
      tiles: layout.tiles.map((tile) =>
        tile === oldVoid ? (TileType.VOID as TileTypeVal) : tile,
      ),
    }
  }

  if (layout.tileColors && layout.tileColors.length === layout.tiles.length) {
    return layout
  }

  const tileColors: Array<FloorColor | null> = []
  for (const tile of layout.tiles) {
    switch (tile) {
      case 0:
        tileColors.push(null)
        break
      case 1:
        tileColors.push(DEFAULT_LEFT_ROOM_COLOR)
        break
      case 2:
        tileColors.push(DEFAULT_RIGHT_ROOM_COLOR)
        break
      case 3:
        tileColors.push({ h: 280, s: 40, b: -5, c: 0 })
        break
      case 4:
        tileColors.push({ h: 35, s: 25, b: 10, c: 0 })
        break
      default:
        tileColors.push(
          tile > 0 && tile !== TileType.VOID ? { h: 0, s: 0, b: 0, c: 0 } : null,
        )
    }
  }

  return { ...layout, tileColors }
}
