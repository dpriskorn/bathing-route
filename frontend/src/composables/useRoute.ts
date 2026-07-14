export interface WikipediaUrl {
  lang: string
  title: string
  url: string
}

export interface SpotDetails {
  qid: string
  label: string
  image_url: string | null
  wikidata_url: string
  wikipedia_urls: WikipediaUrl[]
}

export interface BathingSpotProperties {
  qid: string
  image_url: string | null
  commons_category: string | null
  has_eu_bath: boolean
}

export interface BathingSpotFeature {
  type: 'Feature'
  geometry: {
    type: 'Point'
    coordinates: [number, number]
  }
  properties: BathingSpotProperties
}

export interface RouteFeature {
  type: 'Feature'
  geometry: {
    type: 'LineString'
    coordinates: [number, number][]
  }
  properties: Record<string, never>
}

export interface BufferFeature {
  type: 'Feature'
  geometry: {
    type: 'Polygon'
    coordinates: [number, number][][]
  }
  properties: Record<string, never>
}

export interface AnalyzeResponse {
  bathing_spots: {
    type: 'FeatureCollection'
    features: BathingSpotFeature[]
  }
  route: RouteFeature
  buffer: BufferFeature
}

export type Backend = 'wdqs' | 'qlever' | 'wdqs-all'

export interface LayerFilter {
  has_property?: string[]
  missing_property?: string[]
}

export interface Layer {
  id: string
  name: string
  name_sv: string
  filter: LayerFilter
  color: string
  icon: string
  default_visible: boolean
}

export interface LayerWithCount {
  layer: Layer
  count: number | null
}

export interface CacheInfo {
  backend: string
  count: number
  fetched_at: string | null
  fresh: boolean
  ttl_hours: number
}

const STORAGE_KEY = 'wikidata_spot_details'
const TTL_MS = 7 * 24 * 60 * 60 * 1000

interface CachedEntry {
  details: SpotDetails
  fetched_at: number
}

export function getCachedSpotDetails(qid: string, lang: string): SpotDetails | null {
  try {
    const raw = localStorage.getItem(`${STORAGE_KEY}:${qid}:${lang}`)
    if (!raw) return null
    const entry: CachedEntry = JSON.parse(raw)
    if (Date.now() - entry.fetched_at > TTL_MS) return null
    return entry.details
  } catch {
    return null
  }
}

export function setCachedSpotDetails(qid: string, lang: string, details: SpotDetails): void {
  const entry: CachedEntry = { details, fetched_at: Date.now() }
  localStorage.setItem(`${STORAGE_KEY}:${qid}:${lang}`, JSON.stringify(entry))
}

export function getAllCachedDetails(lang: string): Record<string, SpotDetails> {
  const result: Record<string, SpotDetails> = {}
  try {
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i)
      if (key && key.startsWith(`${STORAGE_KEY}:`) && key.endsWith(`:${lang}`)) {
        const raw = localStorage.getItem(key)
        if (raw) {
          const entry: CachedEntry = JSON.parse(raw)
          if (Date.now() - entry.fetched_at <= TTL_MS) {
            const qid = key.split(':')[1]
            result[qid] = entry.details
          }
        }
      }
    }
  } catch {
    // ignore
  }
  return result
}

export async function getSpotDetails(qid: string, lang: string): Promise<SpotDetails> {
  const cached = getCachedSpotDetails(qid, lang)
  if (cached) return cached

  const response = await fetch(`/api/wikidata/${qid}/details?lang=${lang}`)
  if (!response.ok) throw new Error('Failed to fetch spot details')
  const details: SpotDetails = await response.json()
  setCachedSpotDetails(qid, lang, details)
  return details
}

export async function batchFetchSpotDetails(
  qids: string[],
  lang: string,
  onProgress?: (details: Record<string, SpotDetails>) => void
): Promise<Record<string, SpotDetails>> {
  const uncached = qids.filter(qid => !getCachedSpotDetails(qid, lang))
  const results: Record<string, SpotDetails> = {}

  for (const qid of uncached) {
    const details = await getSpotDetails(qid, lang)
    results[qid] = details
  }

  const all = { ...getAllCachedDetails(lang), ...results }
  if (onProgress) {
    onProgress(all)
  }
  return all
}

export function clearSpotDetailsCache(): void {
  const prefix = `${STORAGE_KEY}:`
  const keys: string[] = []
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i)
    if (key?.startsWith(prefix)) {
      keys.push(key)
    }
  }
  keys.forEach(k => localStorage.removeItem(k))
}

export async function getLayers(): Promise<LayerWithCount[]> {
  const response = await fetch('/api/layers')
  if (!response.ok) throw new Error('Failed to fetch layers')
  const data = await response.json()
  return data as LayerWithCount[]
}

export function filterSpotsByLayer(
  spots: BathingSpotFeature[],
  layer: Layer
): BathingSpotFeature[] {
  const filter = layer.filter
  return spots.filter(spot => {
    const props = spot.properties
    for (const prop of filter.has_property || []) {
      if (prop === 'P9616' && !props.has_eu_bath) return false
      if (prop === 'P18' && !props.image_url) return false
      if (prop === 'P373' && !props.commons_category) return false
    }
    for (const prop of filter.missing_property || []) {
      if (prop === 'P18' && props.image_url) return false
      if (prop === 'P373' && props.commons_category) return false
    }
    return true
  })
}

export function useRoute() {
  const analyze = async (file: File, bufferKm: number, backend: Backend = 'wdqs'): Promise<AnalyzeResponse> => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('buffer_km', bufferKm.toString())
    formData.append('backend', backend)

    const response = await fetch('/api/analyze', {
      method: 'POST',
      body: formData,
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Analysis failed')
    }

    return response.json()
  }

  const getCacheInfo = async (backend: Backend): Promise<CacheInfo> => {
    const response = await fetch(`/api/cache?backend=${backend}`)
    if (!response.ok) {
      throw new Error('Failed to fetch cache info')
    }
    return response.json()
  }

  const clearCache = async (backend?: Backend): Promise<{ deleted_sites: number; deleted_labels: number }> => {
    const url = backend ? `/api/cache?backend=${backend}` : '/api/cache'
    const response = await fetch(url, { method: 'DELETE' })
    if (!response.ok) {
      throw new Error('Failed to clear cache')
    }
    return response.json()
  }

  return { analyze, getCacheInfo, clearCache }
}
