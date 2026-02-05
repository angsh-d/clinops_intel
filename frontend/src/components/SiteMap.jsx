import { memo, useMemo } from 'react'
import {
  ComposableMap,
  Geographies,
  Geography,
  Marker,
  ZoomableGroup,
} from 'react-simple-maps'
import { useNavigate, useParams } from 'react-router-dom'

const geoUrl = 'https://cdn.jsdelivr.net/npm/us-atlas@3/states-10m.json'

const US_CITY_COORDS = {
  'Huntsville': [-86.5861, 34.7304],
  'Mobile': [-88.0399, 30.6954],
  'Springdale': [-94.1288, 36.1867],
  'Bakersfield': [-119.0187, 35.3733],
  'Encinitas': [-117.2917, 33.0370],
  'Los Angeles': [-118.2437, 34.0522],
  'Santa Rosa': [-122.7141, 38.4404],
  'Whittier': [-118.0328, 33.9792],
  'Gainesville': [-82.3248, 29.6516],
  'Evanston': [-87.6876, 42.0451],
  'Portland': [-122.6765, 45.5152],
  'Seattle': [-122.3321, 47.6062],
  'Chicago': [-87.6298, 41.8781],
  'Houston': [-95.3698, 29.7604],
  'Dallas': [-96.7970, 32.7767],
  'Phoenix': [-112.0740, 33.4484],
  'San Diego': [-117.1611, 32.7157],
  'San Francisco': [-122.4194, 37.7749],
  'Boston': [-71.0589, 42.3601],
  'New York': [-74.0060, 40.7128],
  'Philadelphia': [-75.1652, 39.9526],
  'Miami': [-80.1918, 25.7617],
  'Atlanta': [-84.3880, 33.7490],
  'Denver': [-104.9903, 39.7392],
  'Minneapolis': [-93.2650, 44.9778],
  'Detroit': [-83.0458, 42.3314],
  'Cleveland': [-81.6944, 41.4993],
  'Pittsburgh': [-79.9959, 40.4406],
  'Nashville': [-86.7816, 36.1627],
  'Memphis': [-90.0490, 35.1495],
  'New Orleans': [-90.0715, 29.9511],
  'Salt Lake City': [-111.8910, 40.7608],
  'San Antonio': [-98.4936, 29.4241],
  'Austin': [-97.7431, 30.2672],
  'Jacksonville': [-81.6557, 30.3322],
  'Tampa': [-82.4572, 27.9506],
  'Orlando': [-81.3792, 28.5383],
  'Baltimore': [-76.6122, 39.2904],
  'Washington': [-77.0369, 38.9072],
  'Las Vegas': [-115.1398, 36.1699],
  'Raleigh': [-78.6382, 35.7796],
  'Charlotte': [-80.8431, 35.2271],
  'Richmond': [-77.4360, 37.5407],
  'Halifax': [-63.5752, 44.6488],
  'Toronto': [-79.3832, 43.6532],
  'Vancouver': [-123.1207, 49.2827],
  'Montreal': [-73.5673, 45.5017],
  'Calgary': [-114.0719, 51.0447],
  'Edmonton': [-113.4909, 53.5461],
  'Ottawa': [-75.6972, 45.4215],
}

function SiteMap({ sites = [], attentionSites = [], onSiteClick }) {
  const navigate = useNavigate()
  const { studyId } = useParams()

  const markers = useMemo(() => {
    const allSites = sites.length > 0 ? sites : []
    const attentionIds = new Set(attentionSites.map(s => s.id || s.site_id))
    
    const result = allSites
      .filter(site => site.city && US_CITY_COORDS[site.city])
      .map(site => {
        const coords = US_CITY_COORDS[site.city]
        const isAttention = attentionIds.has(site.site_id)
        return {
          id: site.site_id,
          name: site.name,
          city: site.city,
          coordinates: coords,
          isAttention,
        }
      })
    return result
  }, [sites, attentionSites])

  if (sites.length === 0) {
    return (
      <div className="w-full h-full bg-apple-surface rounded-xl border border-apple-border flex items-center justify-center text-apple-secondary text-sm">
        Loading site locations...
      </div>
    )
  }

  const handleMarkerClick = (siteId) => {
    if (onSiteClick) {
      onSiteClick(siteId)
    } else {
      navigate(`/study/${studyId}/site/${siteId}`)
    }
  }

  return (
    <div className="w-full h-full bg-apple-surface rounded-xl border border-apple-border overflow-hidden">
      <ComposableMap
        projection="geoAlbersUsa"
        projectionConfig={{
          scale: 900,
        }}
        style={{ width: '100%', height: '100%' }}
      >
        <ZoomableGroup center={[-96, 38]} zoom={1}>
          <Geographies geography={geoUrl}>
            {({ geographies }) =>
              geographies.map((geo) => (
                <Geography
                  key={geo.rsmKey}
                  geography={geo}
                  fill="#e5e5e5"
                  stroke="#d4d4d4"
                  strokeWidth={0.5}
                  style={{
                    default: { outline: 'none' },
                    hover: { outline: 'none', fill: '#d4d4d4' },
                    pressed: { outline: 'none' },
                  }}
                />
              ))
            }
          </Geographies>

          {markers.map((marker) => (
            <Marker
              key={marker.id}
              coordinates={marker.coordinates}
              onClick={() => handleMarkerClick(marker.id)}
              style={{ cursor: 'pointer' }}
            >
              <circle
                r={marker.isAttention ? 6 : 4}
                fill={marker.isAttention ? '#f59e0b' : '#10b981'}
                stroke="#fff"
                strokeWidth={1.5}
                className="transition-all hover:r-8"
              />
              <title>{marker.name} - {marker.city}</title>
            </Marker>
          ))}
        </ZoomableGroup>
      </ComposableMap>

      <div className="absolute bottom-3 left-3 flex items-center gap-4 text-xs text-apple-secondary bg-white/90 backdrop-blur px-3 py-1.5 rounded-lg">
        <div className="flex items-center gap-1.5">
          <div className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
          <span>Healthy</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-2.5 h-2.5 rounded-full bg-amber-500" />
          <span>Needs Attention</span>
        </div>
      </div>
    </div>
  )
}

export default memo(SiteMap)
