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

  /**
   * 纳入统一调度：动画结束时出栈并回收 isAnimating。
   *
   * 注意 onComplete 只能有一个回调，GSAP 后注册会覆盖先注册，
   * 所以额外的收尾逻辑必须走这里的 onDone 参数，不能在 track 之后再次 eventCallback('onComplete')。
   */
  const track = (timeline: Timeline, onDone?: () => void) => {
    activeTimelines.push(timeline)
    timeline.eventCallback('onComplete', () => {
      const idx = activeTimelines.indexOf(timeline)
      if (idx > -1) activeTimelines.splice(idx, 1)
      if (activeTimelines.length === 0) isAnimating.value = false
      onDone?.()
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
    track(timeline, () => {
      renderer?.setOptions({ tokenOverrides: new Map() })
      redraw()
      onDone?.()
    })
    return timeline
  }

  /**
   * 按棋盘格号走位：由渲染器锚点生成逐格 waypoints。
   * 后端 game.player_moved 只给 from / steps，这里换算成逐格路径（支持绕回起点）。
   */
  const playTokenMoveByPositions = (playerId: number, from: number, steps: number, onDone?: () => void) => {
    if (!renderer) return null
    const anchors = renderer.anchors()
    const total = anchors.size
    if (!total) return null

    const waypoints: TokenPoint[] = []
    for (let i = 0; i < steps; i += 1) {
      const point = anchors.get((from + i) % total)
      if (point) waypoints.push(point)
    }
    const last = anchors.get((from + steps) % total)
    if (last) waypoints.push(last)

    if (waypoints.length < 2) return null
    return playTokenMove(playerId, waypoints, onDone)
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
    playTokenMoveByPositions,
    playCardReveal,
    playMoneyFloat,
    killAll,
  }
}
