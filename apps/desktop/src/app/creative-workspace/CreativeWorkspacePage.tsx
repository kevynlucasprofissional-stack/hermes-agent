import './creative-workspace.css'

import { useEffect, useRef, useState } from 'react'

import { assertCreativeProject, newCreativeProject } from './creative-mvp-model'
import { CreativeGraphEditor } from './CreativeGraphEditor'
import { CreativeInspector } from './CreativeInspector'
import { CreativePreview } from './CreativePreview'
import { CreativeTimeline } from './CreativeTimeline'
import { CreativeToolbar } from './CreativeToolbar'
import { CreativeWorkspaceProvider, useCreativeWorkspace } from './CreativeWorkspaceContext'
import { CreativeWorkspaceSwitcher } from './CreativeWorkspaceSwitcher'

export function CreativeWorkspacePage() {
  return <CreativeWorkspaceProvider><CreativeWorkspaceContent /></CreativeWorkspaceProvider>
}

interface ImportedAsset {
  id: string
  name: string
  type: string
  url: string
}

function CreativeWorkspaceContent() {
  const { project, workspaceMode, pinnedPanels, setProject } = useCreativeWorkspace()
  const fileRef = useRef<HTMLInputElement>(null)
  const [openError, setOpenError] = useState('')
  const assetInputRef = useRef<HTMLInputElement>(null)
  const [assets, setAssets] = useState<ImportedAsset[]>([])
  const assetUrls = useRef<string[]>([])

  // First launch must be a usable editor, not a demand for a nonexistent JSON file.
  useEffect(() => {
    if (!project) {setProject(newCreativeProject(crypto.randomUUID()))}
  }, [project, setProject])

  useEffect(() => () => {
    for (const url of assetUrls.current) {URL.revokeObjectURL(url)}
    assetUrls.current = []
  }, [])

  const importAssets = (files: FileList | null) => {
    if (!files?.length) {return}
    const accepted: ImportedAsset[] = []

    for (const file of Array.from(files).slice(0, 30)) {
      if (!/^(image|video|audio)\//.test(file.type) || file.size > 250_000_000) {
        setOpenError('Escolha imagens, vídeos ou áudios de até 250 MB por arquivo.')

        continue
      }

      const url = URL.createObjectURL(file)
      assetUrls.current.push(url)
      accepted.push({ id: crypto.randomUUID(), name: file.name, type: file.type, url })
    }

    if (accepted.length) {setAssets(current => [...current, ...accepted].slice(-60))}
  }

  const openFile = async (file: File | undefined) => {
    if (!file) {return}

    try {
      if (file.size > 2_000_000) {throw new Error('Project file exceeds 2 MB')}
      const data: unknown = JSON.parse(await file.text())
      assertCreativeProject(data)
      setProject(data)
      setOpenError('')
    } catch (error) {
      setOpenError(error instanceof Error ? error.message : 'Invalid project')
    }
  }

  const showTimeline = pinnedPanels.has('timeline') || workspaceMode === 'montage' || workspaceMode === 'motion'
  const showGraphEditor = pinnedPanels.has('graph-editor') || workspaceMode === 'motion'
  const showInspector = pinnedPanels.has('inspector') || true
  const showPreview = pinnedPanels.has('preview') || true

  if (!project) {
    return (
      <div className="creative-workspace-empty">
        <div className="creative-workspace-welcome">
          <h2>Creative Workspace</h2>
          <p>Create an editable vector project, or open a previously saved JSON project.</p>
          <button onClick={() => setProject(newCreativeProject(crypto.randomUUID()))} type="button">New project</button>
          <button onClick={() => fileRef.current?.click()} type="button">Open project</button>
          <input accept=".json,application/json" aria-label="Project JSON file" onChange={event => void openFile(event.target.files?.[0])} ref={fileRef}
            style={{ display: 'none' }} type="file" />
          {openError && <p role="alert">{openError}</p>}
        </div>
      </div>
    )
  }

  return (
    <div className="creative-workspace-page">
      <CreativeToolbar />
      <div className="creative-workspace-project-bar">
        <strong>{project.name}</strong>
        <button onClick={() => assetInputRef.current?.click()} type="button">Importar assets</button>
        <button onClick={() => fileRef.current?.click()} type="button">Abrir projeto JSON</button>
        <input
          accept="image/*,video/*,audio/*"
          aria-label="Selecionar assets"
          multiple
          onChange={event => {importAssets(event.target.files); event.target.value = ''}}
          ref={assetInputRef}
          style={{ display: 'none' }}
          type="file"
        />
      </div>
      {assets.length > 0 && (
        <section aria-label="Assets importados" className="creative-asset-shelf">
          <span className="creative-asset-note">Pré-visualização somente nesta sessão; estes assets ainda não são salvos no projeto JSON.</span>
          <div className="creative-asset-list">
            {assets.map(asset => (
              <div className="creative-asset" key={asset.id}>
                {asset.type.startsWith('image/') ? <img alt={asset.name} src={asset.url} /> :
                  asset.type.startsWith('video/') ? <video aria-label={asset.name} controls src={asset.url} /> :
                    <audio aria-label={asset.name} controls src={asset.url} />}
                <span title={asset.name}>{asset.name}</span>
              </div>
            ))}
          </div>
        </section>
      )}
      <input accept=".json,application/json" aria-label="Project JSON file" onChange={event => void openFile(event.target.files?.[0])} ref={fileRef}
        style={{ display: 'none' }} type="file" />
      {openError && <p role="alert">{openError}</p>}
      <CreativeWorkspaceSwitcher />

      <div className="creative-workspace-main">
        <div className="creative-workspace-left">
          {showPreview && <CreativePreview />}
        </div>

        <div className="creative-workspace-center">
          {showTimeline && <CreativeTimeline />}
          {showGraphEditor && <CreativeGraphEditor />}
        </div>

        <div className="creative-workspace-right">
          {showInspector && <CreativeInspector />}
        </div>
      </div>
    </div>
  )
}
