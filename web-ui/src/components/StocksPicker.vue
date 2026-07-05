<script setup lang="ts">
// 多标的输入（组合回测用）。逐个添加 6 位代码，市场自动识别。
// 删除手动市场选择（沪市/深市/北交所），由 detectMarket 智能匹配。

import { ref } from 'vue'

import { detectMarket } from '../market'
import StockSearchInput from './StockSearchInput.vue'
import type { StockSearchEntry } from '../types'

const props = defineProps<{
  modelValue: string[]
}>()
const emit = defineEmits<{ 'update:modelValue': [value: string[]] }>()

const code = ref('')

function add() {
  if (!/^\d{6}$/.test(code.value)) return
  const sym = `${detectMarket(code.value)}:${code.value}`
  if (!props.modelValue.includes(sym)) {
    emit('update:modelValue', [...props.modelValue, sym])
  }
  code.value = ''
}

/** 选中下拉建议时，直接添加并清空输入框（组合页"选中即添加"的快捷流） */
function onSelectEntry(entry: StockSearchEntry) {
  const sym = `${detectMarket(entry.code)}:${entry.code}`
  if (!props.modelValue.includes(sym)) {
    emit('update:modelValue', [...props.modelValue, sym])
  }
  code.value = ''
}

function remove(sym: string) {
  emit('update:modelValue', props.modelValue.filter((s) => s !== sym))
}
</script>

<template>
  <div class="stocks-picker">
    <div class="row add-row">
      <StockSearchInput
        v-model="code"
        placeholder="6位代码 / 拼音 / 名字"
        @select="onSelectEntry"
        @confirm="add"
      />
      <button @click="add">添加</button>
    </div>

    <div v-if="modelValue.length" class="stock-list">
      <span v-for="s in modelValue" :key="s" class="stock-tag">
        {{ s }}
        <button class="remove" @click="remove(s)">×</button>
      </span>
    </div>
    <p v-else class="hint">至少添加 1 只标的</p>
  </div>
</template>

<style scoped>
.add-row {
  display: flex;
  gap: 6px;
  align-items: center;
}
/* StockSearchInput 根元素填满剩余宽度 */
.add-row :deep(.stock-search-input) {
  flex: 1;
}
.stock-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}
.stock-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  padding: 3px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-family: var(--font-mono);
}
.remove {
  border: none;
  background: none;
  color: var(--text-dim);
  padding: 0 2px;
  font-size: 14px;
  line-height: 1;
}
.remove:hover {
  color: var(--up);
}
.hint {
  color: var(--text-dim);
  font-size: 11px;
  margin-top: 8px;
}
</style>
