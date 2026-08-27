<template>
  <span
    class="batch-checkbox-custom"
    :class="{ checked, indeterminate }"
    @click.stop="$emit('change')"
  >
    <span v-if="checked || indeterminate" class="check-icon">{{ indeterminate ? '–' : '✓' }}</span>
  </span>
</template>

<script setup>
defineProps({
  checked: {
    type: Boolean,
    default: false
  },
  indeterminate: {
    type: Boolean,
    default: false
  }
})

defineEmits(['change'])
</script>

<style scoped>
.batch-checkbox-custom {
  width: 18px;
  height: 18px;
  border: 2px solid var(--text-disabled);
  border-radius: 4px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
}
.batch-checkbox-custom.checked {
  background: var(--color-blue);
  border-color: var(--color-blue);
}
.batch-checkbox-custom.indeterminate {
  background: var(--bg-card);
  border-color: var(--color-blue);
}
.batch-checkbox-custom.indeterminate .check-icon {
  color: var(--color-blue) !important;
}
.check-icon {
  font-size: 12px;
  color: #fff;
  font-weight: bold;
  line-height: 1;
}
</style>
