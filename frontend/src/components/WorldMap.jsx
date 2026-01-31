import { useState, memo } from 'react'
import { motion } from 'framer-motion'
import {
  ComposableMap,
  Geographies,
  Geography,
  Marker,
  ZoomableGroup
} from 'react-simple-maps'

const geoUrl = 'https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json'

const countryCoordinates = {
  'USA': { lat: 39.8283, lng: -98.5795 },
  'UK': { lat: 55.3781, lng: -3.436 },
  'Japan': { lat: 36.2048, lng: 138.2529 },
  'Germany': { lat: 51.1657, lng: 10.4515 },
  'France': { lat: 46.6034, lng: 1.8883 },
  'Canada': { lat: 56.1304, lng: -106.3468 },
  'JPN': { lat: 36.2048, lng: 138.2529 },
  'DEU': { lat: 51.1657, lng: 10.4515 },
  'FRA': { lat: 46.6034, lng: 1.8883 },
  'CAN': { lat: 56.1304, lng: -106.3468 },
  'GBR': { lat: 55.3781, lng: -3.436 }
}

function getCoordinatesForCountry(country, index = 0) {
  const base = countryCoordinates[country] || { lat: 0, lng: 0 }
  const offset = (index % 10) * 2
  const angle = (index * 137.5) * (Math.PI / 180)
  return [
    base.lng + Math.cos(angle) * offset,
    base.lat + Math.sin(angle) * offset
  ]
}

export const WorldMap = memo(function WorldMap({ sites, onSiteClick, onSiteHover, hoveredSite }) {
  const [position, setPosition] = useState({ coordinates: [10, 40], zoom: 2.5 })

  const countryGroups = {}
  sites.forEach((site, idx) => {
    if (!countryGroups[site.country]) {
      countryGroups[site.country] = []
    }
    countryGroups[site.country].push({ ...site, countryIndex: countryGroups[site.country].length })
  })

  const siteMarkers = sites.map((site, idx) => {
    const countryIdx = countryGroups[site.country]?.findIndex(s => s.id === site.id) || 0
    return {
      ...site,
      coordinates: getCoordinatesForCountry(site.country, countryIdx)
    }
  })

  return (
    <div className="relative h-[400px] bg-apple-bg rounded-xl overflow-hidden border border-apple-border">
      <ComposableMap
        projection="geoMercator"
        projectionConfig={{
          scale: 120,
          center: [0, 30]
        }}
        style={{ width: '100%', height: '100%' }}
      >
        <ZoomableGroup
          zoom={position.zoom}
          center={position.coordinates}
          onMoveEnd={setPosition}
          minZoom={1}
          maxZoom={8}
        >
          <Geographies geography={geoUrl}>
            {({ geographies }) =>
              geographies.map((geo) => (
                <Geography
                  key={geo.rsmKey}
                  geography={geo}
                  fill="#E5E5E5"
                  stroke="#D1D1D6"
                  strokeWidth={0.5}
                  style={{
                    default: { outline: 'none' },
                    hover: { fill: '#D1D1D6', outline: 'none' },
                    pressed: { outline: 'none' }
                  }}
                />
              ))
            }
          </Geographies>

          {siteMarkers.map((site) => (
            <Marker
              key={site.id}
              coordinates={site.coordinates}
              onMouseEnter={() => onSiteHover?.(site)}
              onMouseLeave={() => onSiteHover?.(null)}
              onClick={() => onSiteClick?.(site)}
            >
              <motion.circle
                initial={{ r: 0 }}
                animate={{ r: hoveredSite?.id === site.id ? 8 : 5 }}
                transition={{ type: 'spring', stiffness: 300 }}
                fill={
                  site.status === 'critical' ? '#FF3B30' :
                  site.status === 'warning' ? '#FF9500' :
                  '#1D1D1F'
                }
                stroke="#FFFFFF"
                strokeWidth={1}
                style={{ cursor: 'pointer' }}
                className={site.status === 'critical' ? 'animate-pulse' : ''}
              />
            </Marker>
          ))}
        </ZoomableGroup>
      </ComposableMap>

      <div className="absolute bottom-4 left-4 flex items-center gap-4 text-caption text-apple-secondary">
        <div className="flex items-center gap-1.5">
          <div className="w-2.5 h-2.5 rounded-full bg-apple-text" />
          <span>Healthy</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-2.5 h-2.5 rounded-full bg-apple-warning" />
          <span>Warning</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-2.5 h-2.5 rounded-full bg-apple-critical" />
          <span>Critical</span>
        </div>
      </div>

      <div className="absolute bottom-4 right-4 flex gap-2">
        <button
          onClick={() => setPosition(p => ({ ...p, zoom: Math.min(p.zoom * 1.5, 8) }))}
          className="w-8 h-8 bg-apple-surface border border-apple-border rounded-lg flex items-center justify-center text-apple-text hover:bg-apple-bg transition-colors"
        >
          +
        </button>
        <button
          onClick={() => setPosition(p => ({ ...p, zoom: Math.max(p.zoom / 1.5, 1) }))}
          className="w-8 h-8 bg-apple-surface border border-apple-border rounded-lg flex items-center justify-center text-apple-text hover:bg-apple-bg transition-colors"
        >
          −
        </button>
      </div>

      {hoveredSite && (
        <motion.div
          initial={{ opacity: 0, y: 5 }}
          animate={{ opacity: 1, y: 0 }}
          className="absolute top-4 right-4 card p-3 min-w-48"
        >
          <div className="flex items-center justify-between mb-1">
            <span className="font-medium text-apple-text">{hoveredSite.id}</span>
            <span className={`px-2 py-0.5 rounded-full text-xs text-white ${
              hoveredSite.status === 'critical' ? 'bg-apple-critical' :
              hoveredSite.status === 'warning' ? 'bg-apple-warning' :
              'bg-apple-success'
            }`}>
              {hoveredSite.status}
            </span>
          </div>
          <p className="text-caption text-apple-secondary">{hoveredSite.country}</p>
          <div className="mt-2 pt-2 border-t border-apple-border text-caption">
            <div className="flex justify-between">
              <span className="text-apple-secondary">Enrollment</span>
              <span className="font-mono">{Math.round(hoveredSite.enrollmentPercent)}%</span>
            </div>
          </div>
        </motion.div>
      )}
    </div>
  )
})
