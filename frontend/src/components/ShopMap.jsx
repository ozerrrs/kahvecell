import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png'
import markerIcon from 'leaflet/dist/images/marker-icon.png'
import markerShadow from 'leaflet/dist/images/marker-shadow.png'
import { CircleMarker, MapContainer, Marker, Popup, TileLayer } from 'react-leaflet'
import { Link } from 'react-router-dom'
import { KIZILAY } from '../utils/geo'

// Vite ile paketlenince Leaflet'in varsayılan işaretçi resimleri bulunamaz; elle tanıtıyoruz.
L.Icon.Default.mergeOptions({ iconRetinaUrl: markerIcon2x, iconUrl: markerIcon, shadowUrl: markerShadow })

/**
 * Dükkânları harita üzerinde gösterir.
 * @param shops   ShopSummary listesi (latitude, longitude, name, id …)
 * @param center  Haritanın merkezi ({lat, lng}); kullanıcı konumu varsa o
 * @param userLocation  Verilirse mavi nokta olarak gösterilir
 */
export default function ShopMap({ shops, center = KIZILAY, userLocation, height = 360 }) {
  return (
    <MapContainer
      center={[center.lat, center.lng]}
      zoom={13}
      style={{ height, width: '100%' }}
      className="map"
      scrollWheelZoom={false}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {userLocation && (
        <CircleMarker center={[userLocation.lat, userLocation.lng]} radius={8} pathOptions={{ color: '#2563eb' }}>
          <Popup>Konumunuz</Popup>
        </CircleMarker>
      )}
      {shops.map((shop) => (
        <Marker key={shop.id} position={[shop.latitude, shop.longitude]}>
          <Popup>
            <strong>{shop.name}</strong>
            <br />
            ⭐ {shop.rating} {shop.distance_km != null && `· ${shop.distance_km} km`}
            <br />
            <Link to={`/shops/${shop.id}`}>Detay ve menü →</Link>
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  )
}
