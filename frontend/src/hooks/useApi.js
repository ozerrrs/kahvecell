import { useCallback, useEffect, useState } from 'react'

/**
 * Bir API çağrısını çalıştırır ve yükleniyor / hata / veri durumlarını yönetir.
 *
 *   const { data, loading, error, reload } = useApi(() => shopsApi.list(), [])
 */
export function useApi(fetcher, deps = []) {
  const [state, setState] = useState({ data: null, loading: true, error: null })

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const run = useCallback(fetcher, deps)

  const load = useCallback(() => {
    let cancelled = false
    setState((s) => ({ ...s, loading: true, error: null }))
    run()
      .then((data) => !cancelled && setState({ data, loading: false, error: null }))
      .catch((error) => !cancelled && setState({ data: null, loading: false, error }))
    return () => { cancelled = true }
  }, [run])

  useEffect(() => load(), [load])

  return { ...state, reload: load }
}
