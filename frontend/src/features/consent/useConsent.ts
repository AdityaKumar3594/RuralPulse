import { useCallback, useEffect, useState } from 'react'
import { getConsentStatus } from '../../api/endpoints'
import type { ConsentStatus } from '../../api/types'

export type ConsentState =
  | { phase: 'loading' }
  | { phase: 'error'; error: unknown }
  | { phase: 'ready'; status: ConsentStatus; valid: boolean }

/** Valid means the active consent was given by the person the system requires for this age. */
export function useConsent(): ConsentState & { reload: () => void } {
  const [state, setState] = useState<ConsentState>({ phase: 'loading' })
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    getConsentStatus({ signal: controller.signal })
      .then((status) =>
        setState({
          phase: 'ready',
          status,
          valid: status.active !== null && status.active.given_by === status.required_given_by,
        }),
      )
      .catch((error: unknown) => {
        if (!controller.signal.aborted) setState({ phase: 'error', error })
      })
    return () => controller.abort()
  }, [attempt])

  const reload = useCallback(() => {
    setState({ phase: 'loading' })
    setAttempt((n) => n + 1)
  }, [])
  return { ...state, reload }
}
