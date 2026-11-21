import { useState } from 'react'
import { Link } from 'react-router-dom'
import { shopsApi } from '../api/endpoints'
import ShopMap from '../components/ShopMap'
import { AsyncView } from '../components/StateViews'
import { useApi } from '../hooks/useApi'
import { KIZILAY } from '../utils/geo'

export default function HomePage() {
  // Şimdilik konum olarak Kızılay kullanılıyor; tarayıcı konumu sonraki adımda eklenecek.
  const [location] = useState(KIZILAY)
  const shops = useApi(() => shopsApi.list({ lat: location.lat, lng: location.lng, radius: 20 }), [location])

  return (
    <section>
      <h1>Yakındaki dükkânlar</h1>
      <AsyncView
        {...shops}
        onRetry={shops.reload}
        isEmpty={(page) => page.items.length === 0}
        emptyText="Yakınında anlaşmalı dükkân bulunamadı."
      >
        {(page) => (
          <>
            <ShopMap shops={page.items} center={location} userLocation={location} />
            <ul className="list">
              {page.items.map((shop) => (
                <li key={shop.id} className="card">
                  <Link to={`/shops/${shop.id}`} className="card-link">
                    <div className="row">
                      <strong>{shop.name}</strong>
                      <span className={shop.is_open_now ? 'badge badge-ok' : 'badge'}>
                        {shop.is_open_now ? 'Açık' : 'Kapalı'}
                      </span>
                    </div>
                    <div className="muted">{shop.address}</div>
                    <div className="muted">⭐ {shop.rating} · {shop.distance_km} km</div>
                  </Link>
                </li>
              ))}
            </ul>
          </>
        )}
      </AsyncView>
    </section>
  )
}
