<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import GpxUploader from './components/GpxUploader.vue'
import BufferControl from './components/BufferControl.vue'
import RouteMap from './components/RouteMap.vue'
import {
  batchFetchSpotDetails,
  clearSpotDetailsCache,
  type Backend,
  type CacheInfo,
  type SpotDetails,
  useRoute,
} from './composables/useRoute'

const { t } = useI18n()
const { analyze, getCacheInfo, clearCache } = useRoute()

const locale = ref(localStorage.getItem('locale') || 'sv')
const data = ref<Awaited<ReturnType<typeof analyze>> | null>(null)
const spotDetails = ref<Record<string, SpotDetails>>({})
const loading = ref(false)
const error = ref<string | null>(null)
const bufferKm = ref(10)
const backend = ref<Backend>('wdqs')
const cacheInfo = ref<CacheInfo | null>(null)
const clearingCache = ref(false)

async function refreshCacheInfo() {
  try {
    cacheInfo.value = await getCacheInfo(backend.value)
  } catch {
    cacheInfo.value = null
  }
}

async function prefetchDetails() {
  if (!data.value) return
  const qids = data.value.bathing_spots.features.map(f => f.properties.qid)
  await batchFetchSpotDetails(qids, locale.value, (progress) => {
    spotDetails.value = progress
  })
}

async function handleFileSelected(file: File) {
  error.value = null
  loading.value = true
  try {
    data.value = await analyze(file, bufferKm.value, backend.value)
    await refreshCacheInfo()
    await prefetchDetails()
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Analysis failed'
  } finally {
    loading.value = false
  }
}

async function handleBufferChange(value: number) {
  bufferKm.value = value
  if (data.value) {
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    const file = input?.files?.[0]
    if (file) {
      await handleFileSelected(file)
    }
  }
}

async function handleBackendChange(value: Backend) {
  backend.value = value
  await refreshCacheInfo()
  if (data.value) {
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    const file = input?.files?.[0]
    if (file) {
      await handleFileSelected(file)
    }
  }
}

async function handleLocaleChange() {
  localStorage.setItem('locale', locale.value)
  if (data.value) {
    await prefetchDetails()
  }
}

async function handleClearCache() {
  clearingCache.value = true
  try {
    await clearCache()
    clearSpotDetailsCache()
    cacheInfo.value = null
    data.value = null
    spotDetails.value = {}
    await refreshCacheInfo()
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to clear cache'
  } finally {
    clearingCache.value = false
  }
}
</script>

<template>
  <div class="app">
    <header>
      <h1>EU Bathing Spots Along Route</h1>
    </header>

    <main>
      <aside class="sidebar">
        <GpxUploader @file-selected="handleFileSelected" />
        <BufferControl v-model="bufferKm" @update:model-value="handleBufferChange" />
        <div class="backend-control">
          <label>
            Wikidata backend:
            <select v-model="backend" @change="handleBackendChange(backend)" class="form-select">
              <option value="wdqs">WDQS (default)</option>
              <option value="qlever">QLever</option>
            </select>
          </label>
        </div>
        <div class="language-control">
          <label>
            {{ t('language') }}:
            <select v-model="locale" @change="handleLocaleChange" class="form-select">
              <option value="sv">Svenska</option>
              <option value="en">English</option>
            </select>
          </label>
        </div>
        <div v-if="data" class="stats">
          <p>{{ t('bathingSpotsFound', { count: data.bathing_spots.features.length }) }}</p>
        </div>
        <div v-if="error" class="error">{{ error }}</div>
        <div class="cache-control">
          <div class="cache-info" v-if="cacheInfo">
            <span v-if="cacheInfo.fresh" class="cache-fresh">
              {{ t('cache') }}: {{ cacheInfo.count }} spots ({{ t('fresh') }})
            </span>
            <span v-else class="cache-stale">
              {{ t('cache') }}: {{ cacheInfo.count }} spots ({{ t('stale') }})
            </span>
          </div>
          <button
            class="clear-cache-btn"
            :disabled="clearingCache"
            @click="handleClearCache"
          >
            {{ clearingCache ? '...' : t('clearCache') }}
          </button>
        </div>
      </aside>

      <section class="map-section">
        <RouteMap :data="data" :spot-details="spotDetails" :locale="locale" :loading="loading" />
      </section>
    </main>
  </div>
</template>

<style scoped>
.app {
  display: flex;
  flex-direction: column;
  height: 100vh;
}

header {
  padding: 1rem;
  background: #42b983;
  color: white;
}

header h1 {
  margin: 0;
  font-size: 1.25rem;
}

main {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.sidebar {
  width: 320px;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  background: #f5f5f5;
  overflow-y: auto;
}

.backend-control,
.language-control {
  padding: 0.75rem;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.backend-control label,
.language-control label {
  font-size: 0.9rem;
  color: #333;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.backend-control select,
.language-control select {
  padding: 0.35rem;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 0.9rem;
  cursor: pointer;
}

.stats {
  padding: 0.75rem;
  background: #fff;
  border-radius: 8px;
  font-size: 0.9rem;
}

.stats p {
  margin: 0;
}

.error {
  padding: 0.75rem;
  background: #fee;
  color: #c00;
  border-radius: 8px;
  font-size: 0.9rem;
}

.cache-control {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem;
  background: #fff;
  border-radius: 8px;
  font-size: 0.8rem;
}

.cache-info {
  color: #666;
}

.cache-fresh {
  color: #2a9d3a;
}

.cache-stale {
  color: #e67e22;
}

.clear-cache-btn {
  padding: 0.3rem 0.75rem;
  border: 1px solid #ccc;
  border-radius: 4px;
  background: #fff;
  color: #333;
  font-size: 0.8rem;
  cursor: pointer;
  transition: all 0.2s;
}

.clear-cache-btn:hover:not(:disabled) {
  background: #f0f0f0;
  border-color: #999;
}

.clear-cache-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.map-section {
  flex: 1;
  position: relative;
}
</style>
