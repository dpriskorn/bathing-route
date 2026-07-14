export interface BathingSpotFeature {
  type: 'Feature'
  geometry: {
    type: 'Point'
    coordinates: [number, number]
  }
  properties: {
    qid: string
    label: string
  }
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

export type Backend = 'wdqs' | 'qlever'

export interface CacheInfo {
  backend: string
  count: number
  fetched_at: string | null
  fresh: boolean
  ttl_hours: number
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

  const clearCache = async (backend?: Backend): Promise<{ deleted: number }> => {
    const url = backend ? `/api/cache?backend=${backend}` : '/api/cache'
    const response = await fetch(url, { method: 'DELETE' })
    if (!response.ok) {
      throw new Error('Failed to clear cache')
    }
    return response.json()
  }

  return { analyze, getCacheInfo, clearCache }
}
