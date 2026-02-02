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
  'CAN': { lat: 56.1304, lng: -106.3468 },
  'GBR': { lat: 55.3781, lng: -3.436 },
  'JPN': { lat: 36.2048, lng: 138.2529 },
  'DEU': { lat: 51.1657, lng: 10.4515 },
  'ESP': { lat: 40.4637, lng: -3.7492 },
  'NLD': { lat: 52.1326, lng: 5.2913 },
  'DNK': { lat: 56.2639, lng: 9.5018 },
  'FIN': { lat: 61.9241, lng: 25.7482 },
  'HUN': { lat: 47.1625, lng: 19.5033 },
  'CZE': { lat: 49.8175, lng: 15.473 },
  'RUS': { lat: 55.7558, lng: 37.6173 },
  'TUR': { lat: 38.9637, lng: 35.2433 },
  'KOR': { lat: 35.9078, lng: 127.7669 },
  'TWN': { lat: 23.6978, lng: 120.9605 },
  'AUS': { lat: -25.2744, lng: 133.7751 },
  'NZL': { lat: -40.9006, lng: 174.886 },
  'ARG': { lat: -38.4161, lng: -63.6167 },
  'ISR': { lat: 31.0461, lng: 34.8516 },
  'ZAF': { lat: -30.5595, lng: 22.9375 },
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

export const WorldMap = memo(function WorldMap({ sites, onSiteClick, onSiteHover, hoveredSite, height, highlightedSiteNames }) {
  const highlighted = highlightedSiteNames || new Set()
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
    <div className={`relative ${height || 'h-[400px]'} bg-apple-bg rounded-xl overflow-hidden border border-apple-border`}>
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

          {/* Render non-highlighted sites first, then highlighted on top */}
          {siteMarkers
            .slice()
            .sort((a, b) => (highlighted.has(a.name) ? 1 : 0) - (highlighted.has(b.name) ? 1 : 0))
            .map((site) => {
            const isSignal = highlighted.has(site.name)
            const isHovered = hoveredSite?.id === site.id
            const baseRadius = isSignal ? 7 : 5
            return (
              <Marker
                key={site.id}
                coordinates={site.coordinates}
                onMouseEnter={() => onSiteHover?.(site)}
                onMouseLeave={() => onSiteHover?.(null)}
                onClick={() => onSiteClick?.(site)}
              >
                {/* Animated radar rings — only for intelligence signal sites */}
                {isSignal && (
                  <>
                    <circle r={baseRadius} fill="#5856D6" opacity={0.12}>
                      <animate attributeName="r" from={baseRadius} to={baseRadius + 20} dur="2.5s" repeatCount="indefinite" />
                      <animate attributeName="opacity" from="0.25" to="0" dur="2.5s" repeatCount="indefinite" />
                    </circle>
                    <circle r={baseRadius} fill="#5856D6" opacity={0.12}>
                      <animate attributeName="r" from={baseRadius} to={baseRadius + 20} dur="2.5s" begin="0.8s" repeatCount="indefinite" />
                      <animate attributeName="opacity" from="0.2" to="0" dur="2.5s" begin="0.8s" repeatCount="indefinite" />
                    </circle>
                    <circle r={baseRadius} fill="#5856D6" opacity={0.12}>
                      <animate attributeName="r" from={baseRadius} to={baseRadius + 20} dur="2.5s" begin="1.6s" repeatCount="indefinite" />
                      <animate attributeName="opacity" from="0.15" to="0" dur="2.5s" begin="1.6s" repeatCount="indefinite" />
                    </circle>
                  </>
                )}
                {/* Solid dot */}
                <motion.circle
                  initial={{ r: 0 }}
                  animate={{ r: isHovered ? baseRadius + 3 : baseRadius }}
                  transition={{ type: 'spring', stiffness: 300 }}
                  fill={
                    isSignal ? '#5856D6' :
                    site.status === 'critical' ? '#FF3B30' :
                    site.status === 'warning' ? '#FF9500' :
                    '#1D1D1F'
                  }
                  stroke="#FFFFFF"
                  strokeWidth={isSignal ? 2 : 1}
                  style={{ cursor: 'pointer' }}
                />
              </Marker>
            )
          })}
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
        {highlighted.size > 0 && (
          <div className="flex items-center gap-1.5">
            <div className="relative w-4 h-4 flex items-center justify-center">
              <div className="absolute w-4 h-4 rounded-full bg-[#5856D6]/20 animate-ping" />
              <div className="w-2.5 h-2.5 rounded-full bg-[#5856D6]" />
            </div>
            <span>Active Signal</span>
          </div>
        )}
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
            <span className="font-medium text-apple-text">{hoveredSite.name || hoveredSite.id}</span>
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
