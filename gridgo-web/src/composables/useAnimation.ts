/**
 * useAnimation —— GSAP 动画调度
 *
 * 与 BoardRenderer 协作：动画过程中把中间坐标写入 tokenOverrides 并触发重绘。
 */

import { ref } from 'vue'
import { createCardRevealTimeline, createDiceTimeline, createMoneyFloatTimeline, createTokenMoveTimeline } from '@/game/animations'
import type { BoardRenderer } from '@/game/renderer'
import type { TokenPoint } from '@/game/entities'

/** GSAP 时间线类型（从动画工厂的返回值推导，避免仅为类型引入 gsap 运行时依赖） */
type Timeline = ReturnType<typeof createDiceTimeline>

export function useAnimation() {
  const isAnimating = ref(false)
  const diceValues = ref<number[]>([])
  let renderer: BoardRenderer | null = null
  const activeTimelines: Timeline[] = []

  const bind = (target: BoardRenderer | null) => {
    renderer = target
  }

  const track = (timeline: Timeline) => {
    activeTimelines.push(timeline)
    timeline.eventCallback('onComplete', () => {
      const idx = activeTimelines.indexOf(timeline)
      if (idx > -1) activeTimelines.splice(idx, 1)
      if (activeTimelines.length === 0) isAnimating.value = false
    })
    return timeline
  }

  const redraw = () => renderer?.render()

  /** 骰子滚动动画 */
  const playDice = (finalValues: number[], diceCount = 2) => {
    isAnimating.value = true
    const timeline = createDiceTimeline(
      (values) => {
        diceValues.value = values
        renderer?.setOptions({ centerLines: [`骰子 ${values.join(' + ')}`] })
        redraw()
      },
      finalValues,
      diceCount,
    )
    return track(timeline)
  }

  /** 棋子逐格移动动画 */
  const playTokenMove = (playerId: number, waypoints: TokenPoint[], onDone?: () => void) => {
    if (!renderer) return null
    isAnimating.value = true
    const overrides = new Map<number, TokenPoint>()
    const timeline = createTokenMoveTimeline(
      waypoints,
      (point) => {
        overrides.set(playerId, point)
        renderer?.setOptions({ tokenOverrides: overrides })
        redraw()
      },
      0.12,
    )
    track(timeline)
    timeline.eventCallback('onComplete', () => {
      renderer?.setOptions({ tokenOverrides: new Map() })
      redraw()
      onDone?.()
    })
    return timeline
  }

  /** 卡片翻出动效 */
  const playCardReveal = (target: Element | null) => track(createCardRevealTimeline(target))

  /** 金额飘字 */
  const playMoneyFloat = (target: Element | null, amount: number) => track(createMoneyFloatTimeline(target, amount))

  const killAll = () => {
    activeTimelines.splice(0).forEach((t) => t.kill())
    isAnimating.value = false
    renderer?.setOptions({ tokenOverrides: new Map() })
  }

  return {
    isAnimating,
    diceValues,
    bind,
    redraw,
    playDice,
    playTokenMove,
    playCardReveal,
    playMoneyFloat,
    killAll,
  }
}
