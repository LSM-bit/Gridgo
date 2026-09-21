/**
 * GSAP 动画层
 *
 * 只负责"把状态变化变成一个 GSAP 时间线"，不直接操作 Vue 状态，
 * 通过回调把中间态交给 renderer 重绘。
 */

import gsap from 'gsap'
import type { TokenPoint } from './entities'

export function prefersReducedMotion(): boolean {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return false
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

/** 骰子滚动：先快速跳变，再定格到最终点数 */
export function createDiceTimeline(onTick: (values: number[]) => void, finalValues: number[], diceCount = 2): gsap.core.Timeline {
  const proxy = { frame: 0 }
  const frames = 8
  const timeline = gsap.timeline({
    onUpdate: () => {
      const settled = proxy.frame >= frames
      const values = settled
        ? finalValues
        : Array.from({ length: diceCount }, () => 1 + Math.floor(Math.random() * 6))
      onTick(values)
    },
  })
  timeline.to(proxy, {
    frame: frames,
    duration: prefersReducedMotion() ? 0.01 : 0.7,
    ease: 'power1.out',
    onComplete: () => onTick(finalValues),
  })
  return timeline
}

/** 棋子沿路径逐格移动（waypoints 为逐格锚点序列） */
export function createTokenMoveTimeline(
  waypoints: TokenPoint[],
  onUpdate: (point: TokenPoint) => void,
  durationPerStep = 0.14,
): gsap.core.Timeline {
  const timeline = gsap.timeline()
  if (waypoints.length === 0) return timeline
  const current = { x: waypoints[0].x, y: waypoints[0].y }
  onUpdate({ ...current })
  if (prefersReducedMotion()) {
    const last = waypoints[waypoints.length - 1]
    onUpdate({ ...last })
    return timeline
  }
  waypoints.slice(1).forEach((point) => {
    timeline.to(current, {
      x: point.x,
      y: point.y,
      duration: durationPerStep,
      ease: 'power2.inOut',
      onUpdate: () => onUpdate({ x: current.x, y: current.y }),
    })
  })
  return timeline
}

/** 卡片翻出效果 */
export function createCardRevealTimeline(target: Element | null): gsap.core.Timeline {
  const timeline = gsap.timeline()
  if (!target) return timeline
  if (prefersReducedMotion()) return timeline
  timeline.fromTo(
    target,
    { scale: 0.6, rotateX: -35, opacity: 0 },
    { scale: 1, rotateX: 0, opacity: 1, duration: 0.45, ease: 'back.out(1.6)' },
  )
  return timeline
}

/** 金额飘字（现金增减提示） */
export function createMoneyFloatTimeline(target: Element | null, amount: number): gsap.core.Timeline {
  const timeline = gsap.timeline()
  if (!target) return timeline
  const el = target as HTMLElement
  el.textContent = `${amount >= 0 ? '+' : '-'}$${Math.abs(amount)}`
  el.style.color = amount >= 0 ? '#2e7d32' : '#c62828'
  if (prefersReducedMotion()) {
    return timeline
  }
  timeline.fromTo(
    el,
    { y: 0, opacity: 0, scale: 0.8 },
    { y: -38, opacity: 1, scale: 1.1, duration: 0.35, ease: 'power2.out' },
  )
  timeline.to(el, { opacity: 0, duration: 0.35, delay: 0.15 })
  return timeline
}

/** 高亮闪烁（用于当前可操作地块提示） */
export function createPulseTimeline(target: Element | null): gsap.core.Timeline {
  const timeline = gsap.timeline()
  if (!target || prefersReducedMotion()) return timeline
  timeline.to(target, { opacity: 0.55, duration: 0.5, yoyo: true, repeat: 3, ease: 'sine.inOut' })
  return timeline
}

export { gsap }
