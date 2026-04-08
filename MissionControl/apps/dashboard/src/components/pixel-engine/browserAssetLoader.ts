/**
 * Browser-based asset loader for the pixel engine.
 * Loads PNGs via fetch + Canvas API (no Node.js pngjs dependency).
 */

import type { SpriteData, OfficeLayout } from './types.js'
import { setCharacterTemplates } from './sprites/spriteData.js'
import { setFloorSprites } from './floorTiles.js'
import { setWallSprites } from './wallTiles.js'
import { buildDynamicCatalog } from './layout/furnitureCatalog.js'
import type { LoadedAssetData } from './layout/furnitureCatalog.js'

const ALPHA_THRESHOLD = 2
const CHAR_FRAME_W = 16
const CHAR_FRAME_H = 32
const CHAR_FRAMES_PER_ROW = 7
const CHARACTER_DIRECTIONS = ['down', 'up', 'right'] as const
const FLOOR_TILE_SIZE = 16
const WALL_PIECE_WIDTH = 16
const WALL_PIECE_HEIGHT = 32
const WALL_GRID_COLS = 4
const WALL_BITMASK_COUNT = 16

// ── PNG → SpriteData conversion via Canvas ─────────────────────

function rgbaToHex(r: number, g: number, b: number, a: number): string {
  if (a < ALPHA_THRESHOLD) return ''
  const rgb = `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`.toUpperCase()
  if (a >= 255) return rgb
  return `${rgb}${a.toString(16).padStart(2, '0').toUpperCase()}`
}

async function fetchImageData(url: string): Promise<{ data: Uint8ClampedArray; width: number; height: number }> {
  const img = new Image()
  img.crossOrigin = 'anonymous'
  await new Promise<void>((resolve, reject) => {
    img.onload = () => resolve()
    img.onerror = () => reject(new Error(`Failed to load image: ${url}`))
    img.src = url
  })
  const canvas = document.createElement('canvas')
  canvas.width = img.width
  canvas.height = img.height
  const ctx = canvas.getContext('2d')!
  ctx.drawImage(img, 0, 0)
  const imageData = ctx.getImageData(0, 0, img.width, img.height)
  return { data: imageData.data, width: img.width, height: img.height }
}

function imageDataToSpriteData(
  data: Uint8ClampedArray,
  imgWidth: number,
  region: { x: number; y: number; w: number; h: number },
): SpriteData {
  const sprite: string[][] = []
  for (let y = 0; y < region.h; y++) {
    const row: string[] = []
    for (let x = 0; x < region.w; x++) {
      const idx = ((region.y + y) * imgWidth + (region.x + x)) * 4
      row.push(rgbaToHex(data[idx], data[idx + 1], data[idx + 2], data[idx + 3]))
    }
    sprite.push(row)
  }
  return sprite
}

// ── Character loading ──────────────────────────────────────────

interface CharacterDirectionSprites {
  down: SpriteData[]
  up: SpriteData[]
  right: SpriteData[]
}

async function loadCharacterSprites(basePath: string, count: number): Promise<CharacterDirectionSprites[]> {
  const results: CharacterDirectionSprites[] = []
  for (let i = 0; i < count; i++) {
    try {
      const { data, width } = await fetchImageData(`${basePath}/char_${i}.png`)
      const charData: CharacterDirectionSprites = { down: [], up: [], right: [] }
      for (let dirIdx = 0; dirIdx < CHARACTER_DIRECTIONS.length; dirIdx++) {
        const dir = CHARACTER_DIRECTIONS[dirIdx]
        const rowOffsetY = dirIdx * CHAR_FRAME_H
        const frames: SpriteData[] = []
        for (let f = 0; f < CHAR_FRAMES_PER_ROW; f++) {
          frames.push(imageDataToSpriteData(data, width, {
            x: f * CHAR_FRAME_W,
            y: rowOffsetY,
            w: CHAR_FRAME_W,
            h: CHAR_FRAME_H,
          }))
        }
        charData[dir] = frames
      }
      results.push(charData)
    } catch (e) {
      console.warn(`Failed to load character ${i}:`, e)
    }
  }
  return results
}

// ── Floor tile loading ─────────────────────────────────────────

async function loadFloorTiles(basePath: string, count: number): Promise<SpriteData[]> {
  const tiles: SpriteData[] = []
  for (let i = 0; i < count; i++) {
    try {
      const { data, width } = await fetchImageData(`${basePath}/floor_${i}.png`)
      tiles.push(imageDataToSpriteData(data, width, {
        x: 0, y: 0,
        w: FLOOR_TILE_SIZE,
        h: FLOOR_TILE_SIZE,
      }))
    } catch {
      // Skip missing floor tiles
    }
  }
  return tiles
}

// ── Wall tile loading ──────────────────────────────────────────

async function loadWallTiles(url: string): Promise<SpriteData[]> {
  const { data, width } = await fetchImageData(url)
  const sprites: SpriteData[] = []
  for (let mask = 0; mask < WALL_BITMASK_COUNT; mask++) {
    const ox = (mask % WALL_GRID_COLS) * WALL_PIECE_WIDTH
    const oy = Math.floor(mask / WALL_GRID_COLS) * WALL_PIECE_HEIGHT
    sprites.push(imageDataToSpriteData(data, width, {
      x: ox, y: oy,
      w: WALL_PIECE_WIDTH,
      h: WALL_PIECE_HEIGHT,
    }))
  }
  return sprites
}

// ── Furniture loading ──────────────────────────────────────────

interface FurnitureManifest {
  id: string
  name: string
  category: string
  type: 'asset' | 'group'
  canPlaceOnWalls: boolean
  canPlaceOnSurfaces: boolean
  backgroundTiles: number
  // Asset fields
  file?: string
  width?: number
  height?: number
  footprintW?: number
  footprintH?: number
  // Group fields
  groupType?: string
  rotationScheme?: string
  members?: ManifestNode[]
}

interface ManifestAsset {
  type: 'asset'
  id: string
  file: string
  width: number
  height: number
  footprintW: number
  footprintH: number
  orientation?: string
  state?: string
  frame?: number
  mirrorSide?: boolean
}

interface ManifestGroup {
  type: 'group'
  groupType: 'rotation' | 'state' | 'animation'
  rotationScheme?: string
  orientation?: string
  state?: string
  members: ManifestNode[]
}

type ManifestNode = ManifestAsset | ManifestGroup

interface FlatAsset {
  id: string
  name: string
  label: string
  category: string
  file: string
  width: number
  height: number
  footprintW: number
  footprintH: number
  isDesk: boolean
  canPlaceOnWalls: boolean
  groupId?: string
  canPlaceOnSurfaces?: boolean
  backgroundTiles?: number
  orientation?: string
  state?: string
  mirrorSide?: boolean
  rotationScheme?: string
  animationGroup?: string
  frame?: number
}

interface InheritedProps {
  groupId: string
  name: string
  category: string
  canPlaceOnWalls: boolean
  canPlaceOnSurfaces: boolean
  backgroundTiles: number
  orientation?: string
  state?: string
  rotationScheme?: string
  animationGroup?: string
}

function flattenManifest(node: ManifestNode, inherited: InheritedProps): FlatAsset[] {
  if (node.type === 'asset') {
    const asset = node as ManifestAsset
    const orientation = asset.orientation ?? inherited.orientation
    const state = asset.state ?? inherited.state
    return [{
      id: asset.id,
      name: inherited.name,
      label: inherited.name,
      category: inherited.category,
      file: (asset as any).file || `${asset.id}.png`,
      width: asset.width,
      height: asset.height,
      footprintW: asset.footprintW,
      footprintH: asset.footprintH,
      isDesk: inherited.category === 'desks',
      canPlaceOnWalls: inherited.canPlaceOnWalls,
      canPlaceOnSurfaces: inherited.canPlaceOnSurfaces,
      backgroundTiles: inherited.backgroundTiles,
      groupId: inherited.groupId,
      ...(orientation ? { orientation } : {}),
      ...(state ? { state } : {}),
      ...(asset.mirrorSide ? { mirrorSide: true } : {}),
      ...(inherited.rotationScheme ? { rotationScheme: inherited.rotationScheme } : {}),
      ...(inherited.animationGroup ? { animationGroup: inherited.animationGroup } : {}),
      ...(asset.frame !== undefined ? { frame: asset.frame } : {}),
    }]
  }

  const group = node as ManifestGroup
  const results: FlatAsset[] = []
  for (const member of group.members) {
    const childProps: InheritedProps = { ...inherited }
    if (group.groupType === 'rotation' && group.rotationScheme) {
      childProps.rotationScheme = group.rotationScheme
    }
    if (group.groupType === 'state' && group.orientation) {
      childProps.orientation = group.orientation
    }
    if (group.groupType === 'state' && group.state) {
      childProps.state = group.state
    }
    if (group.groupType === 'animation') {
      const orientationKey = childProps.orientation || 'default'
      const stateKey = childProps.state || 'default'
      childProps.animationGroup = `${childProps.groupId}|${orientationKey}|${stateKey}`
    }
    if (group.orientation && !childProps.orientation) {
      childProps.orientation = group.orientation
    }
    if (group.state && !childProps.state) {
      childProps.state = group.state
    }
    results.push(...flattenManifest(member, childProps))
  }
  return results
}

async function loadFurnitureAssets(basePath: string): Promise<LoadedAssetData | null> {
  // Discover furniture directories by fetching the known set
  const KNOWN_FURNITURE = [
    'BIN', 'BOOKSHELF', 'CACTUS', 'CLOCK', 'COFFEE', 'COFFEE_TABLE',
    'CUSHIONED_BENCH', 'CUSHIONED_CHAIR', 'DESK', 'DOUBLE_BOOKSHELF',
    'HANGING_PLANT', 'LARGE_PAINTING', 'LARGE_PLANT', 'PC', 'PLANT',
    'PLANT_2', 'POT', 'SMALL_PAINTING', 'SMALL_PAINTING_2', 'SMALL_TABLE',
    'SOFA', 'TABLE_FRONT', 'WHITEBOARD', 'WOODEN_BENCH', 'WOODEN_CHAIR',
  ]

  const catalog: LoadedAssetData['catalog'] = []
  const sprites: Record<string, SpriteData> = {}

  for (const furnitureName of KNOWN_FURNITURE) {
    try {
      const manifestUrl = `${basePath}/${furnitureName}/manifest.json`
      const res = await fetch(manifestUrl)
      if (!res.ok) continue
      const manifest = await res.json() as FurnitureManifest

      const inherited: InheritedProps = {
        groupId: manifest.id || furnitureName,
        name: manifest.name || furnitureName,
        category: manifest.category || 'misc',
        canPlaceOnWalls: manifest.canPlaceOnWalls ?? false,
        canPlaceOnSurfaces: manifest.canPlaceOnSurfaces ?? false,
        backgroundTiles: manifest.backgroundTiles ?? 0,
      }

      let assets: FlatAsset[]
      if (manifest.type === 'asset') {
        assets = [{
          id: manifest.id || furnitureName,
          name: manifest.name || furnitureName,
          label: manifest.name || furnitureName,
          category: manifest.category,
          file: manifest.file || `${manifest.id || furnitureName}.png`,
          width: manifest.width!,
          height: manifest.height!,
          footprintW: manifest.footprintW!,
          footprintH: manifest.footprintH!,
          isDesk: manifest.category === 'desks',
          canPlaceOnWalls: manifest.canPlaceOnWalls ?? false,
          canPlaceOnSurfaces: manifest.canPlaceOnSurfaces ?? false,
          backgroundTiles: manifest.backgroundTiles ?? 0,
          groupId: manifest.id || furnitureName,
        }]
      } else {
        assets = []
        for (const member of manifest.members || []) {
          assets.push(...flattenManifest(member, inherited))
        }
      }

      // Load sprite for each asset
      for (const asset of assets) {
        try {
          const { data, width } = await fetchImageData(`${basePath}/${furnitureName}/${asset.file}`)
          sprites[asset.id] = imageDataToSpriteData(data, width, {
            x: 0, y: 0,
            w: asset.width,
            h: asset.height,
          })
          catalog.push({
            id: asset.id,
            label: asset.label,
            category: asset.category,
            width: asset.width,
            height: asset.height,
            footprintW: asset.footprintW,
            footprintH: asset.footprintH,
            isDesk: asset.isDesk,
            groupId: asset.groupId,
            orientation: asset.orientation,
            state: asset.state,
            canPlaceOnSurfaces: asset.canPlaceOnSurfaces,
            backgroundTiles: asset.backgroundTiles,
            canPlaceOnWalls: asset.canPlaceOnWalls,
            mirrorSide: asset.mirrorSide,
            rotationScheme: asset.rotationScheme,
            animationGroup: asset.animationGroup,
            frame: asset.frame,
          })
        } catch {
          console.warn(`Failed to load sprite for ${asset.id}`)
        }
      }
    } catch {
      console.warn(`Failed to load furniture manifest for ${furnitureName}`)
    }
  }

  if (catalog.length === 0) return null
  return { catalog, sprites }
}

// ── Layout loading ─────────────────────────────────────────────

async function loadLayout(url: string): Promise<OfficeLayout | null> {
  try {
    const res = await fetch(url)
    if (!res.ok) return null
    return await res.json() as OfficeLayout
  } catch {
    return null
  }
}

// ── Master loader ──────────────────────────────────────────────

export interface AssetLoadResult {
  layout: OfficeLayout | null
  furnitureAssets: LoadedAssetData | null
}

export async function loadAllAssets(assetsBasePath: string): Promise<AssetLoadResult> {
  console.log('[PixelEngine] Loading assets from', assetsBasePath)

  // Load in parallel: characters, floors, walls, furniture, layout
  const [charSprites, floorSprites, wallSprites, furnitureAssets, layout] = await Promise.all([
    loadCharacterSprites(`${assetsBasePath}/characters`, 6),
    loadFloorTiles(`${assetsBasePath}/floors`, 9),
    loadWallTiles(`${assetsBasePath}/walls/wall_0.png`),
    loadFurnitureAssets(`${assetsBasePath}/furniture`),
    loadLayout(`${assetsBasePath}/default-layout.json`),
  ])

  // Register loaded assets with the engine modules
  if (charSprites.length > 0) {
    setCharacterTemplates(charSprites)
    console.log(`[PixelEngine] Loaded ${charSprites.length} character sprites`)
  }

  if (floorSprites.length > 0) {
    setFloorSprites(floorSprites)
    console.log(`[PixelEngine] Loaded ${floorSprites.length} floor tiles`)
  }

  if (wallSprites.length > 0) {
    setWallSprites(wallSprites)
    console.log(`[PixelEngine] Loaded ${wallSprites.length} wall sprites`)
  }

  if (furnitureAssets) {
    buildDynamicCatalog(furnitureAssets)
    console.log(`[PixelEngine] Loaded ${furnitureAssets.catalog.length} furniture assets`)
  }

  if (layout) {
    console.log(`[PixelEngine] Loaded layout: ${layout.cols}x${layout.rows}`)
  }

  return { layout, furnitureAssets }
}
