<template>
  <SelectFilter
    :model-value="modelValue"
    :options="ispList"
    placeholder="全部网络"
    @update:model-value="$emit('update:modelValue', $event)"
    @change="$emit('change')"
  />
</template>

<script setup>
import { ref, onMounted } from 'vue'
import request from '@/api'
import SelectFilter from './SelectFilter.vue'

defineProps({
  modelValue: { type: String, default: '' },
})

defineEmits(['update:modelValue', 'change'])

const ispList = ref([])

onMounted(async () => {
  try {
    const res = await request.get('/api/hosts/filters')
    ispList.value = res?.isps || []
  } catch (e) {
    console.error('获取运营商列表失败:', e)
  }
})
</script>
