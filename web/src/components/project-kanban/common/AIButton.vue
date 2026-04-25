<template>
  <button class="pk-ai-btn" :aria-label="`AI分析: ${title}`" @click="$emit('click')">
    <span class="pk-ai-btn__dot"></span>
    <span class="pk-ai-btn__text">AI</span>
  </button>
</template>

<script setup>
defineProps({
  title: { type: String, default: '' }
})
defineEmits(['click'])
</script>

<style scoped>
.pk-ai-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 10px;
  background: transparent;
  border: 1px solid rgba(99, 102, 241, 0.35);
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
  outline: none;
}
.pk-ai-btn:hover {
  transform: scale(1.05);
  background: rgba(99, 102, 241, 0.06);
  border-color: rgba(99, 102, 241, 0.55);
}
.pk-ai-btn:active {
  transform: scale(0.97);
}
.pk-ai-btn__dot {
  width: 6px;
  height: 6px;
  background: rgba(99, 102, 241, 0.55);
  border-radius: 50%;
  animation: pk-ai-pulse 2s ease-in-out infinite;
}
.pk-ai-btn__text {
  font-size: 12px;
  font-weight: 600;
  color: rgba(99, 102, 241, 0.75);
  letter-spacing: 0.5px;
}
@keyframes pk-ai-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
</style>
