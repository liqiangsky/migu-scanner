<template>
  <SelectFilter
    :model-value="modelValue"
    :options="provinces"
    placeholder="全部地区"
    @update:model-value="$emit('update:modelValue', $event)"
    @change="$emit('change')"
  />
</template>

<script setup>
import { provinces } from '@/data'
import SelectFilter from './SelectFilter.vue'

defineProps({
  modelValue: { type: String, default: '' },
})

defineEmits(['update:modelValue', 'change'])
</script>
