import { useCallback } from 'react'

import { useCreativeWorkspace } from './CreativeWorkspaceContext'
import type { CreativeClip, CreativeTrack } from './types'

export function CreativeTimeline() {
  const { project, selection, playheadTime, setPlayheadTime, selectClip, selectTrack, workspaceMode } = useCreativeWorkspace()
  const composition = project?.compositions[0]
  const tracks = composition?.tracks ?? []

  const trackHeight = 80
  const headerHeight = 40
  const timeRulerHeight = 30
  const pixelsPerSecond = 100

  const totalDuration = project?.duration ?? 60
  const timelineWidth = totalDuration * pixelsPerSecond

  const handleTrackClick = useCallback((trackId: string, e: React.MouseEvent) => {
    selectTrack(trackId, e.shiftKey || e.metaKey || e.ctrlKey)
  }, [selectTrack])

  const handleClipClick = useCallback((clipId: string, e: React.MouseEvent) => {
    selectClip(clipId, e.shiftKey || e.metaKey || e.ctrlKey)
  }, [selectClip])

  const handleTimeRulerClick = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect()
    const x = e.clientX - rect.left
    const time = x / pixelsPerSecond
    setPlayheadTime(Math.max(0, Math.min(totalDuration, time)))
  }, [pixelsPerSecond, totalDuration, setPlayheadTime])

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    const frames = Math.floor((seconds % 1) * 30)

    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}:${frames.toString().padStart(2, '0')}`
  }

  if (!composition) {return null}

  return (
    <div aria-label="Timeline" className="creative-timeline" role="region">
      <div className="creative-timeline-header">
        <div className="creative-timeline-track-headers" style={{ height: headerHeight }}>
          <div className="creative-timeline-track-header" style={{ width: '200px' }}>
            <strong>Tracks</strong>
          </div>
        </div>
        <div
          className="creative-timeline-time-ruler"
          onClick={handleTimeRulerClick}
          style={{ height: timeRulerHeight, width: timelineWidth }}
        >
          {Array.from({ length: Math.ceil(totalDuration) }, (_, i) => (
            <div
              className="creative-timeline-time-marker"
              key={i}
              style={{ left: i * pixelsPerSecond }}
            >
              <span className="creative-timeline-time-label">{formatTime(i)}</span>
              <div className="creative-timeline-time-line" />
            </div>
          ))}
        </div>
      </div>

      <div className="creative-timeline-body">
        <div className="creative-timeline-track-list" style={{ width: '200px' }}>
          {tracks.map((track: CreativeTrack) => (
            <div
              className={`creative-timeline-track ${track.locked ? 'locked' : ''} ${track.muted ? 'muted' : ''} ${selection.selectedTrackIds.has(track.trackId) ? 'selected' : ''}`}
              key={track.trackId}
              onClick={e => handleTrackClick(track.trackId, e)}
              style={{ height: trackHeight }}
            >
              <div className="creative-timeline-track-info">
                <span className="creative-timeline-track-kind">{track.kind}</span>
                <span className="creative-timeline-track-name">{track.name}</span>
                {track.locked && <span className="creative-timeline-track-lock" title="Locked">🔒</span>}
                {track.muted && <span className="creative-timeline-track-mute" title="Muted">🔇</span>}
                {track.solo && <span className="creative-timeline-track-solo" title="Solo">S</span>}
              </div>
            </div>
          ))}
        </div>

        <div className="creative-timeline-clips-area" style={{ width: timelineWidth }}>
          {tracks.map((track: CreativeTrack) => (
            <div
              className={`creative-timeline-track-clips ${track.locked ? 'locked' : ''}`}
              key={track.trackId}
              style={{ height: trackHeight }}
            >
              {track.clips.map((clip: CreativeClip) => {
                const startX = clip.timelineRange.start * pixelsPerSecond
                const clipWidth = (clip.timelineRange.end - clip.timelineRange.start) * pixelsPerSecond
                const isSelected = selection.selectedClipIds.has(clip.clipId)

                return (
                  <div
                    className={`creative-timeline-clip ${isSelected ? 'selected' : ''} ${clip.reverse ? 'reverse' : ''} ${clip.freeze ? 'freeze' : ''} ${clip.speed !== 1 ? 'speed-changed' : ''}`}
                    key={clip.clipId}
                    onClick={e => handleClipClick(clip.clipId, e)}
                    style={{
                      left: startX,
                      width: Math.max(clipWidth, 20),
                    }}
                    title={`${clip.name} (${formatTime(clip.timelineRange.start)} - ${formatTime(clip.timelineRange.end)})`}
                  >
                    <div className="creative-timeline-clip-name">{clip.name}</div>
                    {clip.speed !== 1 && (
                      <div className="creative-timeline-clip-speed">{clip.speed}x</div>
                    )}
                    {clip.reverse && <div className="creative-timeline-clip-reverse">↺</div>}
                    {clip.freeze && <div className="creative-timeline-clip-freeze">❚❚</div>}
                  </div>
                )
              })}
            </div>
          ))}

          <div
            aria-label={`Playhead at ${formatTime(playheadTime)}`}
            className="creative-timeline-playhead"
            style={{ left: playheadTime * pixelsPerSecond }}
          >
            <div className="creative-timeline-playhead-line" />
            <div className="creative-timeline-playhead-time">{formatTime(playheadTime)}</div>
          </div>
        </div>
      </div>
    </div>
  )
}
