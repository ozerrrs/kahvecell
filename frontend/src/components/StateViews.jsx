/** Yükleniyor / hata / boş durum göstergeleri — her sayfada aynı görünüm. */

export function Loading({ text = 'Yükleniyor…' }) {
  return (
    <div className="state" role="status" aria-live="polite">
      <span className="spinner" aria-hidden="true" />
      {text}
    </div>
  )
}

export function ErrorState({ error, onRetry }) {
  return (
    <div className="state state-error" role="alert">
      <p>{error?.message ?? 'Bir şeyler ters gitti.'}</p>
      {onRetry && (
        <button type="button" className="btn btn-secondary" onClick={onRetry}>
          Tekrar dene
        </button>
      )}
    </div>
  )
}

export function Empty({ text, children }) {
  return (
    <div className="state">
      <p>{text}</p>
      {children}
    </div>
  )
}

/** Tek satırda üç durumu birden ele alır; veri hazırsa children(data) çizilir. */
export function AsyncView({ loading, error, data, onRetry, isEmpty, emptyText = 'Henüz bir şey yok.', children }) {
  if (loading) return <Loading />
  if (error) return <ErrorState error={error} onRetry={onRetry} />
  if (isEmpty?.(data)) return <Empty text={emptyText} />
  return children(data)
}
