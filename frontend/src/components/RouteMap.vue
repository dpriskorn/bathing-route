<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  LMap,
  LPolygon,
  LPolyline,
  LTileLayer,
} from '@vue-leaflet/vue-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

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
}>()

const { t } = useI18n()

const map = ref<any>(null)

const zoom = ref(6)
const center = ref<[number, number]>([58.0, 14.0])

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

function buildPopupHtml(spot: BathingSpotFeature): string {
  const details = props.spotDetails[spot.properties.qid]
  if (!details) {
    return `<div class="p-2"><a href="https://www.wikidata.org/wiki/${spot.properties.qid}" target="_blank">${spot.properties.qid}</a></div>`
  }
  if (details.wikipedia_urls.length === 0) {
    console.info(`Wikipedia link missing for ${spot.properties.qid}`)
  }
  let html = '<div class="p-2" style="min-width: 220px; max-width: 320px;">'
  if (details.image_url) {
    html += `<a href="${details.image_url}" target="_blank" rel="noopener"><img src="${details.image_url}?width=400" class="img-fluid mb-2" style="max-height: 200px;" /></a>`
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

const poiMarkers = ref<Map<string, L.CircleMarker>>(new Map())

const poiStyle: L.CircleMarkerOptions = {
  radius: 6,
  color: '#42b983',
  fillColor: '#42b983',
  fillOpacity: 0.8,
  weight: 2,
}

function clearMarkers() {
  const leaflet = map.value?.leafletObject
  if (!leaflet) return
  for (const marker of poiMarkers.value.values()) {
    try {
      leaflet.removeLayer(marker)
    } catch {
      // ignore
    }
  }
  poiMarkers.value.clear()
}

function updatePoiMarkers() {
  const leaflet = map.value?.leafletObject
  if (!leaflet) return

  clearMarkers()

  for (const spot of bathingSpots.value) {
    const marker = L.circleMarker(
      [spot.geometry.coordinates[1], spot.geometry.coordinates[0]],
      poiStyle
    )
    marker.bindPopup(buildPopupHtml(spot))
    marker.addTo(leaflet)
    poiMarkers.value.set(spot.properties.qid, marker)
  }
}

function refreshPopups() {
  for (const spot of bathingSpots.value) {
    const marker = poiMarkers.value.get(spot.properties.qid)
    if (marker) {
      marker.setPopupContent(buildPopupHtml(spot))
    }
  }
}

watch(() => props.data, () => {
  nextTick(() => updatePoiMarkers())
})

watch(() => props.spotDetails, () => {
  nextTick(() => refreshPopups())
}, { deep: true })

watch(() => props.locale, () => {
  nextTick(() => refreshPopups())
})

function onMapReady() {
  nextTick(() => updatePoiMarkers())
}
</script>

<template>
  <div class="map-container">
    <LMap
      ref="map"
      v-model:zoom="zoom"
      v-model:center="center"
      :use-global-leaflet="false"
      style="height: 100%; width: 100%"
      @ready="onMapReady"
    >
      <LTileLayer
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        attribution='&copy; <a href="https://openstreetmap.org/copyright">OpenStreetMap</a>'
      />

      <LPolyline
        v-if="routeCoords.length > 0"
        :lat-lngs="routeCoords"
        color="#42b983"
        :weight="4"
      />

      <LPolygon
        v-if="bufferCoords.length > 0"
        :lat-lngs="bufferCoords"
        color="#42b983"
        fill-color="#42b983"
        :fill-opacity="0.1"
        :weight="2"
      />
    </LMap>

    <div v-if="loading" class="loading-overlay">
      <div class="spinner"></div>
    </div>

    <div v-if="!data && !loading" class="placeholder">
      <p>{{ t('uploadPrompt') }}</p>
    </div>
  </div>
</template>

<style scoped>
.map-container {
  position: relative;
  height: 100%;
  width: 100%;
  border-radius: 8px;
  overflow: hidden;
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
