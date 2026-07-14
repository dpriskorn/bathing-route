<script setup lang="ts">
import { ref } from 'vue'

const emit = defineEmits<{
  fileSelected: [file: File]
}>()

const fileInput = ref<HTMLInputElement | null>(null)
const isDragging = ref(false)

function handleDrop(e: DragEvent) {
  isDragging.value = false
  const file = e.dataTransfer?.files[0]
  if (file && file.name.endsWith('.gpx')) {
    emit('fileSelected', file)
  }
}

function handleDragOver(e: DragEvent) {
  isDragging.value = true
  e.preventDefault()
}

function handleDragLeave() {
  isDragging.value = false
}

function handleFileInput(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (file) {
    emit('fileSelected', file)
  }
}

function triggerFileSelect() {
  fileInput.value?.click()
}
</script>

<template>
  <div
    class="uploader"
    :class="{ dragging: isDragging }"
    @drop.prevent="handleDrop"
    @dragover="handleDragOver"
    @dragleave="handleDragLeave"
    @click="triggerFileSelect"
  >
    <input
      ref="fileInput"
      type="file"
      accept=".gpx"
      hidden
      @change="handleFileInput"
    />
    <div class="uploader-content">
      <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
        <polyline points="17 8 12 3 7 8"/>
        <line x1="12" y1="3" x2="12" y2="15"/>
      </svg>
      <p>Drop GPX file here or click to select</p>
      <p class="hint">GraphHopper export recommended</p>
    </div>
  </div>
</template>

<style scoped>
.uploader {
  border: 2px dashed #ccc;
  border-radius: 8px;
  padding: 2rem;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
  background: #fafafa;
}

.uploader:hover,
.uploader.dragging {
  border-color: #42b983;
  background: #f0fdf4;
}

.uploader-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  color: #666;
}

.uploader-content svg {
  color: #42b983;
}

.uploader-content p {
  margin: 0;
}

.uploader-content .hint {
  font-size: 0.8rem;
  color: #999;
}
</style>
