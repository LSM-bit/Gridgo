<template>
  <el-dialog :model-value="modelValue" :title="tile?.name ?? ''" width="380px" @update:model-value="emit('update:modelValue', $event)">
    <div v-if="tile" class="tile-detail">
      <p><strong>类型：</strong>{{ tileTypeText(tile.tile_type) }}</p>
      <p v-if="tile.tile_group"><strong>分组：</strong>{{ tile.tile_group }}</p>
      <p v-if="tile.price"><strong>价格：</strong>{{ formatMoney(tile.price) }}</p>
      <p v-if="tile.build_cost"><strong>建造费：</strong>{{ formatMoney(tile.build_cost) }}</p>
      <p v-if="tile.owner_id"><strong>拥有者：</strong>{{ ownerName || '未知' }}</p>
      <p><strong>建筑等级：</strong>{{ tile.build_level }} / {{ maxBuildLevel }}</p>
      <p v-if="tile.is_mortgaged"><el-tag type="warning">已抵押</el-tag></p>
      <div v-if="tile.rent_0 !== null" class="rent-table">
        <strong>租金表：</strong>
        <table>
          <tr><td>空地</td><td>{{ formatMoney(tile.rent_0) }}</td></tr>
          <tr><td>1 房</td><td>{{ formatMoney(tile.rent_1) }}</td></tr>
          <tr><td>2 房</td><td>{{ formatMoney(tile.rent_2) }}</td></tr>
          <tr><td>3 房</td><td>{{ formatMoney(tile.rent_3) }}</td></tr>
          <tr><td>4 房</td><td>{{ formatMoney(tile.rent_4) }}</td></tr>
          <tr><td>酒店</td><td>{{ formatMoney(tile.rent_5) }}</td></tr>
        </table>
      </div>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { formatMoney, tileTypeText } from '@/utils/format'
import type { TileState } from '@/types/game'

withDefaults(
  defineProps<{
    modelValue: boolean
    tile: TileState | null
    ownerName?: string
    maxBuildLevel?: number
  }>(),
  { ownerName: '', maxBuildLevel: 5 },
)

const emit = defineEmits<{ (e: 'update:modelValue', value: boolean): void }>()
</script>

<style scoped>
.tile-detail {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.tile-detail p {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin: 0;
  padding: 7px 12px;
  border-radius: var(--gg-radius-xs);
  background: var(--gg-surface-2);
  font-size: 13.5px;
  color: var(--gg-ink-2);
}

.tile-detail p strong {
  color: var(--gg-ink-3);
  font-weight: 500;
}

.rent-table {
  margin-top: 6px;
}

.rent-table strong {
  display: block;
  margin-bottom: 6px;
  font-size: 13px;
  color: var(--gg-ink-3);
  font-weight: 500;
}

.rent-table table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0 3px;
}

.rent-table td {
  padding: 6px 12px;
  font-size: 13px;
  background: var(--gg-surface);
  border-top: 1px solid var(--gg-border);
  border-bottom: 1px solid var(--gg-border);
}

.rent-table td:first-child {
  border-left: 1px solid var(--gg-border);
  border-radius: var(--gg-radius-xs) 0 0 var(--gg-radius-xs);
  color: var(--gg-ink-3);
}

.rent-table td:last-child {
  border-right: 1px solid var(--gg-border);
  border-radius: 0 var(--gg-radius-xs) var(--gg-radius-xs) 0;
  text-align: right;
  font-weight: 600;
  color: var(--gg-gold-strong);
  font-variant-numeric: tabular-nums;
}
</style>
