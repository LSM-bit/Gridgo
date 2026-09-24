<template>
  <div ref="wrapper" class="game-board">
    <canvas ref="canvasEl" class="game-board__canvas" @click="handleClick"></canvas>
  </div>
</template>

<script setup lang="ts">
/**
 * Canvas 2D 棋盘组件
 *
 * 页面只负责传入快照与高亮参数；绘制、命中测试、像素尺寸自适应均在渲染层内部完成。
 */
import { computed, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import { BoardRenderer, fitBoardSize } from '@/game/renderer'
import type { RenderOptions } from '@/game/renderer'
import type { GameState } from '@/types/game'

const props = withDefaults(
  defineProps<{
    state: GameState | null
    currentUserId: number
    highlight?: number[]
    selected?: number | null
    centerTitle?: string
    centerLines?: string[]
  }>(),
  {
    highlight: () => [],
    selected: null,
    centerTitle: 'GridGo',
    centerLines: () => [],
  },
)

const emit = defineEmits<{ (e: 'select', position: number): void }>()

const wrapper = ref<HTMLDivElement | null>(null)
const canvasEl = ref<HTMLCanvasElement | null>(null)
const renderer = shallowRef<BoardRenderer | null>(null)
let observer: ResizeObserver | null = null

const syncOptions = (extra: Partial<RenderOptions> = {}) => {
  renderer.value?.setOptions({
    currentUserId: props.currentUserId,
    highlight: props.highlight,
    selected: props.selected,
    centerTitle: props.centerTitle,
    centerLines: props.centerLines,
    ...extra,
  })
}

const render = () => renderer.value?.render()

const draw = (extra: Partial<RenderOptions> = {}) => {
  const instance = renderer.value
  if (!instance) return
  syncOptions(extra)
  instance.render()
}

/**
 * 按容器可用空间（宽 × 高）计算正方形棋盘边长并重绘。
 * 关键：同时受限于宽与高，避免只按宽度放大导致纵向被外层裁切。
 */
const resize = () => {
  const el = wrapper.value
  const instance = renderer.value
  if (!el || !instance) return
  const box = el.getBoundingClientRect()
  instance.setSize(fitBoardSize(box.width, box.height, 4))
  if (props.state) instance.setState(props.state)
  syncOptions()
  instance.render()
}

/**
 * 点击命中优先级：棋子（玩家）> 地块。
 * 用户点击棋子时想看的是"这个玩家"，而不是棋子所在格子的地块信息。
 */
const handleClick = (event: MouseEvent) => {
  const instance = renderer.value
  if (!instance) return
  const userId = instance.playerAt(event.clientX, event.clientY)
  if (userId !== null) {
    emit('select-player', userId)
    return
  }
  const position = instance.tileAt(event.clientX, event.clientY)
  if (position !== null && position !== undefined) emit('select', position)
}

onMounted(() => {
  if (!canvasEl.value) return
  renderer.value = new BoardRenderer(canvasEl.value)
  resize()
  if (typeof ResizeObserver !== 'undefined') {
    observer = new ResizeObserver(() => resize())
    if (wrapper.value) observer.observe(wrapper.value)
  }
  window.addEventListener('resize', resize)
})

onBeforeUnmount(() => {
  observer?.disconnect()
  observer = null
  window.removeEventListener('resize', resize)
  renderer.value?.destroy()
  renderer.value = null
})

watch(
  () => props.state,
  (state) => {
    if (!state || !renderer.value) return
    renderer.value.setState(state)
    draw()
  },
  { deep: false },
)

watch(
  () => [props.highlight, props.selected, props.currentUserId, props.centerLines] as const,
  () => draw(),
)

defineExpose({
  renderer,
  render,
  draw,
  resize,
  /** 命中测试：客户端坐标 → 地块 position */
  tileAt: (x: number, y: number) => renderer.value?.tileAt(x, y) ?? null,
  /** 命中测试：客户端坐标 → 玩家 user_id */
  playerAt: (x: number, y: number) => renderer.value?.playerAt(x, y) ?? null,
  /** 动画期间覆盖棋子坐标（useAnimation 调用） */
  setTokenOverrides: (overrides: Map<number, { x: number; y: number }>) => {
    renderer.value?.setOptions({ tokenOverrides: overrides })
    render()
  },
  boardSize: computed(() => renderer.value?.boardSize ?? 0),
})
</script>

<style scoped>
/**
 * 棋盘容器：高度严格跟随父容器（100%），
 * 不设 min-height，避免在矮视口下把棋盘顶出可视区造成裁切。
 */
.game-board {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  min-height: 0;
  padding: 10px;
  box-sizing: border-box;
  background: var(--gg-bg-deep);
  background-image: var(--gg-grid);
  overflow: hidden;
}

/* 铜金内框 + 齿孔边 */
.game-board::after {
  content: '';
  position: absolute;
  inset: 6px;
  border: 1px solid var(--gg-border-strong);
  box-shadow: inset 0 0 0 3px var(--gg-gold-soft);
  pointer-events: none;
}

.game-board__canvas {
  max-width: 100%;
  max-height: 100%;
  box-shadow: var(--gg-shadow-2);
  cursor: pointer;
  transition: box-shadow var(--gg-dur) var(--gg-ease);
}

.game-board:hover .game-board__canvas {
  box-shadow: var(--gg-shadow-3);
}

@media (max-width: 900px) {
  .game-board {
    min-height: 300px;
    padding: 6px;
  }
}
</style>
