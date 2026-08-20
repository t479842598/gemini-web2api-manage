import { useEffect, useCallback, useRef, useState } from "react"

export function usePolling<T>(
  fetcher: () => Promise<T>,
  intervalMs: number,
  enabled = true,
  deps: readonly unknown[] = [],
) {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const cancelRef = useRef(false)
  const fetchRef = useRef(0)
  // Keep the fetcher in a ref so `start` stays stable across renders. An inline
  // arrow fetcher (e.g. `() => api.config()`) would otherwise change identity on
  // every render, restarting the polling effect and racing `refresh()` results.
  const fetcherRef = useRef(fetcher)
  useEffect(() => {
    fetcherRef.current = fetcher
  }, [fetcher])

  const start = useCallback(async (id: number) => {
    try {
      const result = await fetcherRef.current()
      if (cancelRef.current || id !== fetchRef.current) return
      setData(result)
      setError(null)
    } catch (err: unknown) {
      if (cancelRef.current || id !== fetchRef.current) return
      setError(err instanceof Error ? err.message : "请求失败")
    } finally {
      if (!cancelRef.current && id === fetchRef.current) {
        setLoading(false)
      }
    }
  }, [])

  const refresh = useCallback(() => {
    const id = ++fetchRef.current
    setLoading(true)
    void start(id)
  }, [start])

  useEffect(() => {
    if (!enabled) return

    ++fetchRef.current
    cancelRef.current = false

    const poll = async () => {
      // 每次 tick 读取当前 id：refresh()/deps 刷新递增 id 会作废在途旧请求，
      // 但轮询循环本身必须继续沿用最新 id，否则手动刷新后自动轮询会永久失效。
      await start(fetchRef.current)
      if (!cancelRef.current && intervalMs > 0) {
        await new Promise((r) => setTimeout(r, intervalMs))
        if (!cancelRef.current) poll()
      }
    }

    void poll()

    return () => {
      cancelRef.current = true
    }
  }, [intervalMs, enabled, start])

  // 筛选条件（deps）变化时立即按最新条件刷新，不等下一个轮询周期。
  // 首次挂载跳过（初始 poll 已发起），避免与初始请求并发重复。
  const firstDepsRef = useRef(true)
  useEffect(() => {
    if (!enabled) return
    if (firstDepsRef.current) {
      firstDepsRef.current = false
      return
    }
    refresh()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, ...deps])

  return { data, loading, error, refresh }
}
