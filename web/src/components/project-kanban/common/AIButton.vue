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
  background: linear-gradient(135deg, var(--pk-group-v3), var(--pk-group-v2));
  border: none;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
  outline: none;
}
.pk-ai-btn:hover {
  transform: scale(1.05);
  box-shadow: 0 2px 8px rgba(139, 92, 246, 0.35);
}
.pk-ai-btn:active {
  transform: scale(0.97);
}
.pk-ai-btn__dot {
  width: 6px;
  height: 6px;
  background: var(--pk-card-bg);
  border-radius: 50%;
  animation: pk-ai-pulse 2s ease-in-out infinite;
}
.pk-ai-btn__text {
  font-size: 12px;
  font-weight: 600;
  color: var(--pk-card-bg);
  letter-spacing: 0.5px;
}
@keyframes pk-ai-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
</style>
