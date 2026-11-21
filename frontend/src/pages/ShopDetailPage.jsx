import { Link, useParams } from 'react-router-dom'
import { shopsApi } from '../api/endpoints'
import { AsyncView } from '../components/StateViews'
import { useApi } from '../hooks/useApi'
import { KIZILAY } from '../utils/geo'

const formatTime = (value) => value.slice(0, 5)

export default function ShopDetailPage() {
  const { shopId } = useParams()
  const shop = useApi(() => shopsApi.get(shopId, KIZILAY), [shopId])

  return (
    <AsyncView {...shop} onRetry={shop.reload}>
      {(s) => (
        <section>
          <p><Link to="/">← Dükkânlar</Link></p>
          <h1>{s.name}</h1>
          <p className="muted">{s.address}</p>
          <p className="muted">
            ⭐ {s.rating} · {s.distance_km} km · {formatTime(s.opens_at)}–{formatTime(s.closes_at)} ·{' '}
            {s.is_open_now ? 'Şu an açık' : 'Şu an kapalı'}
          </p>
          {s.description && <p>{s.description}</p>}

          <h2>Menü</h2>
          {s.menu.map((category) => (
            <div key={category.category}>
              <h3>{category.category}</h3>
              <ul className="list">
                {category.items.map((product) => (
                  <li key={product.id} className="card row">
                    <div>
                      <strong>{product.name}</strong>
                      <div className="muted">{product.description}</div>
                    </div>
                    <Link className="btn btn-small" to={`/shops/${s.id}/order?product=${product.id}`}>
                      Sipariş ver
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </section>
      )}
    </AsyncView>
  )
}
