<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

import { batchFetchImageUrls, type CommonsImageInfo } from '../utils/commonsApi'
import type {
  AnalyzeResponse,
  BathingSpotFeature,
  SpotDetails,
} from '../composables/useRoute'

const props = defineProps<{
  data: AnalyzeResponse | null
  spotDetails: Record<string, SpotDetails>
  locale: string
  loading: boolean
  visibleQids: string[]
}>()

const { t } = useI18n()

const mapContainer = ref<HTMLDivElement | null>(null)
let map: L.Map | null = null
let routeLayer: L.Polyline | null = null
let bufferLayer: L.Polygon | null = null
let poiLayer: L.GeoJSON | null = null

const zoom = ref(6)
const center: L.LatLngExpression = [58.0, 14.0]
const commonsUrlCache = ref<Record<string, CommonsImageInfo>>({})
const loadingQids = ref<Set<string>>(new Set())

const emit = defineEmits<{
  'fetch-spot': [qid: string]
}>()

const routeCoords = computed<[number, number][]>(() => {
  if (!props.data) return []
  return props.data.route.geometry.coordinates.map(([lon, lat]) => [lat, lon])
})

const bufferCoords = computed<[number, number][][]>(() => {
  if (!props.data) return []
  return props.data.buffer.geometry.coordinates.map((ring) =>
    ring.map(([lon, lat]) => [lat, lon] as [number, number])
  )
})

const bathingSpots = computed<BathingSpotFeature[]>(() => {
  if (!props.data) return []
  return props.data.bathing_spots.features
})

function buildPopupHtml(qid: string): string {
  const spot = bathingSpots.value.find(s => s.properties.qid === qid)
  if (!spot) return `<div class="p-2">${qid}</div>`
  const details = props.spotDetails[qid]
  if (!details) {
    if (loadingQids.value.has(qid)) {
      console.log('[RouteMap] Showing loading spinner for:', qid)
      return `<div class="p-2"><div class="spinner-border spinner-border-sm" role="status"></div> ${t('loading')}...</div>`
    }
    console.log('[RouteMap] No details for:', qid)
    return `<div class="p-2"><a href="https://www.wikidata.org/wiki/${qid}" target="_blank">${qid}</a></div>`
  }
  if (details.wikipedia_urls.length === 0) {
    console.info(`Wikipedia link missing for ${qid}`)
  }
  let html = '<div class="p-2" style="min-width: 220px; max-width: 320px;">'
  if (details.image_url) {
    const filename = details.image_url.includes('Special:FilePath/')
      ? details.image_url.split('Special:FilePath/').pop()!
      : details.image_url
    const cached = commonsUrlCache.value[filename]
    if (cached?.thumburl) {
      html += `<a href="${cached.url}" target="_blank" rel="noopener"><img src="${cached.thumburl}" class="img-fluid mb-2" style="max-height: 200px;" /></a>`
    } else if (details.image_url) {
      html += `<a href="${details.image_url}" target="_blank" rel="noopener"><img src="${details.image_url}?width=400" class="img-fluid mb-2" style="max-height: 200px;" /></a>`
    }
  }
  html += `<h6>${details.label}</h6>`
  html += '<div class="mb-1">'
  html += `<a href="${details.wikidata_url}" target="_blank" class="text-primary">${t('wikidata')}</a>`
  if (details.wikipedia_urls.length > 0) {
    html += ' | '
    html += details.wikipedia_urls.map(w => `<a href="${w.url}" target="_blank">${w.lang}</a>`).join(' ')
  }
  html += '</div></div>'
  return html
}

const poiStyle: L.CircleMarkerOptions = {
  radius: 6,
  color: '#42b983',
  fillColor: '#42b983',
  fillOpacity: 0.8,
  weight: 2,
}

function updateRouteLayer() {
  if (routeLayer) {
    routeLayer.remove()
    routeLayer = null
  }
  if (!map || routeCoords.value.length === 0) return
  routeLayer = L.polyline(routeCoords.value, {
    color: '#42b983',
    weight: 4,
  }).addTo(map)
}

function updateBufferLayer() {
  if (bufferLayer) {
    bufferLayer.remove()
    bufferLayer = null
  }
  if (!map || bufferCoords.value.length === 0) return
  bufferLayer = L.polygon(bufferCoords.value, {
    color: '#42b983',
    fillColor: '#42b983',
    fillOpacity: 0.1,
    weight: 2,
  }).addTo(map)
}

function updatePoiLayer() {
  if (poiLayer) {
    poiLayer.remove()
    poiLayer = null
  }
  if (!map || bathingSpots.value.length === 0) return

  const visibleSpots = bathingSpots.value.filter(spot => props.visibleQids.includes(spot.properties.qid))

  const geojson: GeoJSON.FeatureCollection = {
    type: 'FeatureCollection',
    features: visibleSpots.map(spot => ({
      type: 'Feature',
      geometry: {
        type: 'Point',
        coordinates: [spot.geometry.coordinates[0], spot.geometry.coordinates[1]],
      },
      properties: { qid: spot.properties.qid },
    })),
  }

  poiLayer = L.geoJSON(geojson, {
    pointToLayer: (_, latlng) => L.circleMarker(latlng, poiStyle),
    onEachFeature: (feature, layer) => {
      const qid = feature.properties!.qid
      layer.bindPopup(() => buildPopupHtml(qid))
      layer.on('click', () => {
        console.log('[RouteMap] Marker clicked:', qid, 'hasDetails:', !!props.spotDetails[qid], 'isLoading:', loadingQids.value.has(qid))
        if (!props.spotDetails[qid] && !loadingQids.value.has(qid)) {
          loadingQids.value.add(qid)
          emit('fetch-spot', qid)
          console.log('[RouteMap] Emitted fetch-spot:', qid)
        }
      })
    },
  }).addTo(map)
}

function fitBounds() {
  if (!map || !props.data) return

  const route = routeCoords.value
  const buffer = bufferCoords.value

  if (route.length === 0) return

  const allCoords: [number, number][] = []

  allCoords.push(...route)
  for (const ring of buffer) {
    allCoords.push(...ring)
  }

  if (allCoords.length === 0) return

  const bounds = L.latLngBounds(allCoords)
  map.fitBounds(bounds, { padding: [50, 50] })
}

function updateAllLayers() {
  updateRouteLayer()
  updateBufferLayer()
  updatePoiLayer()
  fitBounds()
}

watch(() => props.data, () => {
  updateAllLayers()
}, { deep: true })

watch(() => props.visibleQids, () => {
  nextTick(() => updatePoiLayer())
})

watch(() => props.spotDetails, async () => {
  console.log('[RouteMap] spotDetails updated, keys:', Object.keys(props.spotDetails))
  for (const qid of loadingQids.value) {
    if (props.spotDetails[qid]) {
      loadingQids.value.delete(qid)
    }
  }

  const filenames = Object.values(props.spotDetails)
    .filter(d => d.image_url && d.image_url.includes('Special:FilePath/'))
    .map(d => d.image_url!.split('Special:FilePath/').pop()!)
  console.log('[RouteMap] Filenames to fetch images for:', filenames)

  if (filenames.length > 0) {
    const newUrls = await batchFetchImageUrls(filenames)
    console.log('[RouteMap] Got image URLs:', newUrls)
    commonsUrlCache.value = { ...commonsUrlCache.value, ...newUrls }
  }

  if (poiLayer) {
    poiLayer.eachLayer((layer) => {
      const marker = layer as L.CircleMarker
      if (marker.getPopup()) {
        const content = marker.getPopup()?.getContent()
        if (typeof content === 'string' && content.includes('</div>')) {
          const qidMatch = content.match(/wikidata\.org\/wiki\/([A-Z0-9]+)/)
          if (qidMatch) {
            marker.setPopupContent(buildPopupHtml(qidMatch[1]))
          }
        }
      }
    })
  }
}, { deep: true })

watch(commonsUrlCache, () => {
  console.log('[RouteMap] commonsUrlCache updated, keys:', Object.keys(commonsUrlCache.value))
  if (poiLayer) {
    poiLayer.eachLayer((layer) => {
      const marker = layer as L.CircleMarker
      if (marker.getPopup()) {
        const content = marker.getPopup()?.getContent()
        if (typeof content === 'string' && content.includes('</div>')) {
          const qidMatch = content.match(/wikidata\.org\/wiki\/([A-Z0-9]+)/)
          if (qidMatch) {
            marker.setPopupContent(buildPopupHtml(qidMatch[1]))
          }
        }
      }
    })
  }
}, { deep: true })

watch(() => props.locale, () => {
  if (poiLayer) {
    poiLayer.eachLayer((layer) => {
      const marker = layer as L.CircleMarker
      if (marker.getPopup()) {
        const content = marker.getPopup()?.getContent()
        if (typeof content === 'string' && content.includes('</div>')) {
          const qidMatch = content.match(/wikidata\.org\/wiki\/([A-Z0-9]+)/)
          if (qidMatch) {
            marker.setPopupContent(buildPopupHtml(qidMatch[1]))
          }
        }
      }
    })
  }
})

onMounted(() => {
  if (!mapContainer.value) return

  map = L.map(mapContainer.value, {
    center,
    zoom: zoom.value,
  })

  L.tileLayer(
    'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    {
      attribution: '&copy; <a href="https://openstreetmap.org/copyright">OpenStreetMap</a>',
    }
  ).addTo(map)

  map.on('zoomend', () => {
    zoom.value = map!.getZoom()
  })

  updateAllLayers()
})

onUnmounted(() => {
  if (map) {
    map.remove()
    map = null
  }
})
</script>

<template>
  <div class="map-wrapper">
    <div ref="mapContainer" class="map-container"></div>

    <div v-if="loading" class="loading-overlay">
      <div class="spinner"></div>
    </div>

    <div v-if="!data && !loading" class="placeholder">
      <p>{{ t('uploadPrompt') }}</p>
    </div>
  </div>
</template>

<style scoped>
.map-wrapper {
  position: relative;
  height: 100%;
  width: 100%;
}

.map-container {
  height: 100%;
  width: 100%;
  border-radius: 8px;
}

.loading-overlay {
  position: absolute;
  inset: 0;
  background: rgba(255, 255, 255, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #eee;
  border-top-color: #42b983;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #999;
  pointer-events: none;
}
</style>
