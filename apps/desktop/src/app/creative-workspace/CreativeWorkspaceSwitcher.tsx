import { useCreativeWorkspace } from './CreativeWorkspaceContext'

export function CreativeWorkspaceSwitcher() {
  const { workspaceMode, setWorkspaceMode, pinnedPanels, togglePinPanel } = useCreativeWorkspace()

  const modes: Array<{ id: 'montage' | 'motion' | 'design' | '3d' | 'transcript'; label: string; icon: string; panels: string[] }> = [
    { id: 'montage', label: 'Montage', icon: '✂', panels: ['timeline', 'preview', 'inspector'] },
    { id: 'motion', label: 'Motion', icon: '🎬', panels: ['timeline', 'graph-editor', 'preview', 'inspector'] },
    { id: 'design', label: 'Design', icon: '🎨', panels: ['preview', 'inspector'] },
    { id: '3d', label: '3D', icon: '📦', panels: ['preview', 'inspector'] },
    { id: 'transcript', label: 'Transcript', icon: '📝', panels: ['preview', 'inspector'] },
  ]

  return (
    <div aria-label="Workspace modes" className="creative-workspace-switcher" role="tablist">
      {modes.map(mode => {
        const isActive = workspaceMode === mode.id
        const isPinned = mode.panels.some(p => pinnedPanels.has(p))

        return (
          <button
            aria-label={`${mode.label} workspace`}
            aria-selected={isActive}
            className={`creative-workspace-mode-btn ${isActive ? 'active' : ''} ${isPinned ? 'pinned' : ''}`}
            key={mode.id}
            onClick={() => setWorkspaceMode(mode.id)}
            role="tab"
          >
            <span className="creative-workspace-mode-icon">{mode.icon}</span>
            <span className="creative-workspace-mode-label">{mode.label}</span>
            {isPinned && <span className="creative-workspace-mode-pin" title="Pinned panels">📌</span>}
          </button>
        )
      })}
    </div>
  )
}
