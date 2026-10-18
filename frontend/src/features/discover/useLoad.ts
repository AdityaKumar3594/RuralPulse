import { useCallback, useEffect, useState } from 'react'

export type Loaded<T> = { phase: 'loading' } | { phase: 'error'; error: unknown } | { phase: 'ready'; data: T }

type Loader<T> = (options: { signal: AbortSignal }) => Promise<T>

/**
 * Loads data when `load` changes (wrap it in useCallback with its inputs) and on `reload()`.
 * While the inputs change, the state is "loading" again, so old data is never shown for new inputs.
 */
export function useLoad<T>(load: Loader<T>) {
  const [attempt, setAttempt] = useState(0)
  const [settled, setSettled] = useState<{ load: Loader<T>; attempt: number; out: Loaded<T> } | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    load({ signal: controller.signal }).then(
      (data) => setSettled({ load, attempt, out: { phase: 'ready', data } }),
      (error: unknown) => {
        if (!controller.signal.aborted) setSettled({ load, attempt, out: { phase: 'error', error } })
      },
    )
    return () => controller.abort()
  }, [load, attempt])

  const state: Loaded<T> =
    settled && settled.load === load && settled.attempt === attempt ? settled.out : { phase: 'loading' }

  const reload = useCallback(() => setAttempt((n) => n + 1), [])
  /** Replace the loaded data with a newer copy from the server (e.g. after an update). */
  const setData = useCallback(
    (data: T) => setSettled({ load, attempt, out: { phase: 'ready', data } }),
    [load, attempt],
  )
  return { state, reload, setData }
}
