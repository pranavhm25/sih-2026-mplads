import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { CircleMarker, MapContainer, Popup, TileLayer } from 'react-leaflet'
import type { ProjectSummary } from '../types/types'
import { formatINR, signalLabel } from '../lib/format'

interface MapProps {
  points: ProjectSummary[]
}

function getMarkerColor(priorityLevel?: string | null): { stroke: string; fill: string } {
  switch (priorityLevel) {
    case 'CRITICAL':
    case 'HIGH':
      return { stroke: '#9b2617', fill: '#cf3a27' }
    case 'MEDIUM':
      return { stroke: '#995a12', fill: '#c97a1e' }
    default:
      return { stroke: '#525a66', fill: '#7d8694' }
  }
}

export default function CommandCenterMap({ points }: MapProps) {
  const [mounted, setMounted] = useState(false)
  const [filterPriority, setFilterPriority] = useState<string>('ALL')

  useEffect(() => {
    setMounted(true)
  }, [])

  const validPoints = points.filter(
    (p) =>
      p.latitude !== null &&
      p.latitude !== undefined &&
      p.longitude !== null &&
      p.longitude !== undefined &&
      !isNaN(p.latitude) &&
      !isNaN(p.longitude)
  )

  const filteredPoints =
    filterPriority === 'ALL'
      ? validPoints
      : filterPriority === 'HIGH_CRIT'
        ? validPoints.filter((p) => p.priority?.level === 'CRITICAL' || p.priority?.level === 'HIGH')
        : validPoints.filter((p) => p.priority?.level === filterPriority)

  if (!mounted) {
    return (
      <div className="flex h-[360px] w-full items-center justify-center border border-rule bg-paper">
        <p className="font-plex text-[12.5px] text-ink-faint">Loading geographic map…</p>
      </div>
    )
  }

  // Default center roughly on central/southern India where demo works are concentrated
  const defaultCenter: [number, number] = [15.3, 76.5]

  return (
    <div className="border border-ink/60 bg-paper">
      {/* Header bar / Filters */}
      <div className="flex flex-wrap items-center justify-between border-b border-rule px-4 py-2.5 bg-canvas/40">
        <div className="flex items-center gap-3">
          <span className="section-title">Geographic Distribution</span>
          <span className="num text-[11px] text-ink-faint">
            {filteredPoints.length} of {validPoints.length} geotagged works
          </span>
        </div>

        {/* Legend & quick filter */}
        <div className="flex items-center gap-2 text-[11.5px]">
          <button
            onClick={() => setFilterPriority('ALL')}
            className={`px-2 py-0.5 font-plex font-medium transition-colors ${
              filterPriority === 'ALL'
                ? 'bg-ink text-paper'
                : 'text-ink-soft hover:bg-accent-soft'
            }`}
          >
            All
          </button>
          <button
            onClick={() => setFilterPriority('HIGH_CRIT')}
            className={`inline-flex items-center gap-1.5 px-2 py-0.5 font-plex font-medium transition-colors ${
              filterPriority === 'HIGH_CRIT'
                ? 'bg-vermilion text-white'
                : 'text-vermilion hover:bg-verms-soft'
            }`}
          >
            <span className="h-2 w-2 rounded-full bg-vermilion" />
            Critical / High
          </button>
          <button
            onClick={() => setFilterPriority('MEDIUM')}
            className={`inline-flex items-center gap-1.5 px-2 py-0.5 font-plex font-medium transition-colors ${
              filterPriority === 'MEDIUM'
                ? 'bg-amber-signal text-white'
                : 'text-amber-signal hover:bg-amber-soft'
            }`}
          >
            <span className="h-2 w-2 rounded-full bg-amber-signal" />
            Medium
          </button>
          <button
            onClick={() => setFilterPriority('LOW')}
            className={`inline-flex items-center gap-1.5 px-2 py-0.5 font-plex font-medium transition-colors ${
              filterPriority === 'LOW'
                ? 'bg-ink-soft text-white'
                : 'text-ink-soft hover:bg-accent-soft'
            }`}
          >
            <span className="h-2 w-2 rounded-full bg-slate-400" />
            Low
          </button>
        </div>
      </div>

      {/* Map canvas */}
      <div className="relative h-[360px] w-full">
        <MapContainer
          center={defaultCenter}
          zoom={5}
          scrollWheelZoom={false}
          className="h-full w-full z-0"
          style={{ background: '#f5f4ef' }}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            maxZoom={18}
          />
          {filteredPoints.map((p) => {
            const { stroke, fill } = getMarkerColor(p.priority?.level)
            const radius =
              p.priority?.level === 'CRITICAL'
                ? 8
                : p.priority?.level === 'HIGH'
                  ? 7
                  : 5.5
            return (
              <CircleMarker
                key={p.id}
                center={[p.latitude!, p.longitude!]}
                radius={radius}
                pathOptions={{
                  color: stroke,
                  fillColor: fill,
                  fillOpacity: 0.85,
                  weight: 1.5,
                }}
              >
                <Popup className="drishti-popup">
                  <div className="max-w-[260px] text-[12px] leading-tight">
                    <div className="flex items-center justify-between gap-2 border-b border-rule pb-1.5">
                      <span className="font-mono text-[11px] font-semibold text-ink">
                        {p.work_id}
                      </span>
                      {p.priority && (
                        <span
                          className={`font-plex text-[10px] font-semibold uppercase ${
                            p.priority.level === 'CRITICAL' || p.priority.level === 'HIGH'
                              ? 'text-vermilion'
                              : p.priority.level === 'MEDIUM'
                                ? 'text-amber-signal'
                                : 'text-ink-faint'
                          }`}
                        >
                          {p.priority.level} ({p.priority.score.toFixed(1)})
                        </span>
                      )}
                    </div>
                    <p className="mt-1.5 font-medium line-clamp-2 text-ink">
                      {p.description}
                    </p>
                    <p className="mt-1 text-meta text-ink-soft">
                      {p.district}, {p.state} · {formatINR(p.sanctioned_cost)}
                    </p>
                    {p.primary_signals && p.primary_signals.length > 0 && (
                      <div className="mt-1.5 flex flex-wrap gap-1">
                        {p.primary_signals.map((sig) => (
                          <span
                            key={sig}
                            className="bg-paper px-1 py-0.5 border border-rule font-mono text-[9.5px] text-ink-soft"
                          >
                            {signalLabel(sig)}
                          </span>
                        ))}
                      </div>
                    )}
                    <div className="mt-2.5 pt-1.5 border-t border-rule text-right">
                      <Link
                        to={`/projects/${p.id}`}
                        className="font-plex text-[11.5px] font-medium text-accent hover:underline"
                      >
                        Open Intelligence →
                      </Link>
                    </div>
                  </div>
                </Popup>
              </CircleMarker>
            )
          })}
        </MapContainer>
      </div>
    </div>
  )
}
