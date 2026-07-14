<script setup lang="ts">
import { ref, watch } from 'vue'

const props = defineProps<{
  modelValue: number
}>()

const emit = defineEmits<{
  'update:modelValue': [value: number]
}>()

const min = 1
const max = 50

function handleInput(e: Event) {
  const value = parseFloat((e.target as HTMLInputElement).value)
  emit('update:modelValue', value)
}
</script>

<template>
  <div class="buffer-control">
    <label>
      Buffer: <strong>{{ modelValue }} km</strong>
    </label>
    <input
      type="range"
      :min="min"
      :max="max"
      :value="modelValue"
      step="1"
      @input="handleInput"
    />
    <div class="range-labels">
      <span>{{ min }} km</span>
      <span>{{ max }} km</span>
    </div>
  </div>
</template>

<style scoped>
.buffer-control {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  padding: 0.75rem 1rem;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.buffer-control label {
  font-size: 0.9rem;
  color: #333;
}

.buffer-control input[type="range"] {
  width: 100%;
  cursor: pointer;
}

.range-labels {
  display: flex;
  justify-content: space-between;
  font-size: 0.75rem;
  color: #999;
}
</style>
