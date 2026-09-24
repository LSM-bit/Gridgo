import { onBeforeUnmount, ref, watch, type Ref } from 'vue'

/**
 * 本地倒计时
 *
 * 服务端只下发倒计时初值、不逐秒推送，剩余秒数必须由前端自己递减。
 * 本 composable 统一处理"取初值 → 每秒递减 → 归零停表 → 初值/进度变化即重置"，
 * 避免各处自写 setInterval 时漏掉重置或漏掉清理。
 *
 * @param total 当前倒计时初值（秒）；返回 null / ≤0 表示当前没有倒计时
 * @param key   重置键；值变化表示服务端重置了计时器，本地应重新从初值开始
 */
export function useLocalCountdown(
  total: () => number | null | undefined,
  key: () => unknown,
  intervalMs = 1000,
): { secondsLeft: Ref<number>; running: Ref<boolean>; restart: () => void } {
  const secondsLeft = ref(0)
  const running = ref(false)
  let ticker: ReturnType<typeof setInterval> | null = null

  const stop = () => {
    if (ticker !== null) {
      clearInterval(ticker)
      ticker = null
    }
    running.value = false
  }

  const restart = () => {
    stop()
    const value = total()
    if (value === null || value === undefined || value <= 0) {
      secondsLeft.value = 0
      return
    }
    secondsLeft.value = value
    running.value = true
    ticker = setInterval(() => {
      if (secondsLeft.value > 0) {
        secondsLeft.value -= 1
      } else {
        stop()
      }
    }, intervalMs)
  }

  watch([key, total], restart, { immediate: true })
  onBeforeUnmount(stop)

  return { secondsLeft, running, restart }
}
