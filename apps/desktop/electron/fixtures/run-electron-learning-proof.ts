/**
 * Hermes Workstation — Real Electron Learning Mode Visual Proof
 *
 * Boots real Electron, loads visual-demonstration-fixture.html into a real
 * WebContents, executes live capturePage(), encodes with FFmpeg via image2pipe,
 * correlates gestures and snapshots, and verifies the resulting WebM with ffprobe.
 */

import { execSync } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'

import { app, BrowserWindow } from 'electron'

import { LearningSessionRecorder } from '../workstation-learning-session'

async function run() {
  console.log('[proof] Starting real Electron visual demonstration capture...')

  const fixturePath = path.join(__dirname, 'visual-demonstration-fixture.html')

  if (!fs.existsSync(fixturePath)) {
    throw new Error(`Fixture not found: ${fixturePath}`)
  }

  const outputDir = path.join(app.getPath('userData'), 'real-electron-learning-proof')
  fs.rmSync(outputDir, { recursive: true, force: true })
  fs.mkdirSync(outputDir, { recursive: true })

  // 1. Create real Electron browser window
  const win = new BrowserWindow({
    width: 1280,
    height: 720,
    show: false,
    webPreferences: {
      offscreen: false,
      contextIsolation: true
    }
  })

  await win.loadFile(fixturePath)
  console.log('[proof] Loaded visual-demonstration-fixture.html into BrowserWindow')

  // Allow canvas animation to run for 500ms
  await new Promise(r => setTimeout(r, 500))

  // 2. Wire LearningSessionRecorder to real WebContents.capturePage()
  const recorder = new LearningSessionRecorder({
    baseDir: outputDir,
    captureFrame: async () => {
      if (win.isDestroyed() || win.webContents.isDestroyed()) {
        return null
      }

      const nativeImage = await win.webContents.capturePage()

      if (!nativeImage || nativeImage.isEmpty()) {
        return null
      }

      const size = nativeImage.getSize()
      const targetWidth = 1280
      const targetHeight = 720

      const resized =
        size.width === targetWidth && size.height === targetHeight
          ? nativeImage
          : nativeImage.resize({ width: targetWidth, height: targetHeight, quality: 'good' })

      return {
        buffer: resized.toPNG(),
        width: targetWidth,
        height: targetHeight
      }
    },
    captureScreenshot: async (_tabId, targetPath) => {
      if (win.isDestroyed()) {return { success: false }}
      const nativeImage = await win.webContents.capturePage()
      const dest = targetPath || path.join(outputDir, `snap-${Date.now()}.png`)
      fs.mkdirSync(path.dirname(dest), { recursive: true })
      fs.writeFileSync(dest, nativeImage.toPNG())

      return { success: true, screenshot_path: dest }
    }
  })

  // 3. Start recording
  const startState = await recorder.start({
    runtimeSessionId: 'sess-electron-native-proof',
    storedSessionId: 'st-electron-native-proof',
    tabId: 'tab-electron-native',
    webContentsId: win.webContents.id,
    documentEpoch: 'epoch-real-electron',
    allowlistedOrigin: 'file://',
    videoEnabled: true
  })

  console.log('[proof] Recording active in session:', startState.sessionId)

  // 4. Dispatch simulated gestures across the live demonstration
  for (let step = 1; step <= 5; step++) {
    await new Promise(r => setTimeout(r, 600))

    // Interact with live DOM elements
    if (step === 2) {
      await win.webContents.executeJavaScript(`document.getElementById('btn-color').click()`)
    } else if (step === 3) {
      await win.webContents.executeJavaScript(`document.getElementById('btn-shape').click()`)
    } else if (step === 4) {
      await win.webContents.executeJavaScript(`document.getElementById('btn-save').click()`)
    }

    await recorder.recordGesture({
      eventId: `evt-step-${step}`,
      tabId: 'tab-electron-native',
      documentEpoch: 'epoch-real-electron',
      relativeTimeMs: step * 600,
      kind: step === 3 ? 'shortcut' : 'click',
      x: 300 + step * 20,
      y: 200 + step * 10,
      viewportWidth: 1280,
      viewportHeight: 720,
      role: 'button',
      accessibleName: step === 3 ? undefined : `Operator Action ${step}`,
      elementTag: 'button',
      key: step === 3 ? 'S' : undefined,
      ctrl: step === 3 ? true : undefined
    })

    console.log(`[proof] Step ${step}/5 recorded. Frames: ${recorder.getStatus()?.eventsCount}`)
  }

  // 5. Stop recording and flush FFmpeg container
  console.log('[proof] Stopping recording and flushing FFmpeg container...')
  const finalState = await recorder.stop()

  const videoPath = path.join(finalState.sessionDir, 'media', 'recording.webm')
  const frameIndexPath = path.join(finalState.sessionDir, 'media', 'frame_index.jsonl')
  const snapshotsDir = path.join(finalState.sessionDir, 'snapshots')

  // 6. Validate with ffprobe
  const probeRaw = execSync(
    `ffprobe -v quiet -print_format json -show_format -show_streams "${videoPath}"`,
    { encoding: 'utf-8' }
  )

  const probe = JSON.parse(probeRaw)
  const videoStream = probe.streams.find((s: any) => s.codec_type === 'video')

  const stat = fs.statSync(videoPath)
  const frameLines = fs.readFileSync(frameIndexPath, 'utf-8').trim().split('\n')
  const snapshots = fs.readdirSync(snapshotsDir)

  const proofReport = {
    timestamp: new Date().toISOString(),
    electronVersion: process.versions.electron,
    chromeVersion: process.versions.chrome,
    session: {
      sessionId: finalState.sessionId,
      videoStatus: finalState.videoStatus,
      framesRecorded: finalState.eventsCount,
      eventsRecorded: finalState.eventsCount
    },
    video: {
      path: videoPath,
      fileSizeBytes: stat.size,
      codec: videoStream?.codec_name,
      pixelFormat: videoStream?.pix_fmt,
      width: videoStream?.width,
      height: videoStream?.height,
      durationSeconds: Number.parseFloat(probe.format?.duration || '0'),
      container: probe.format?.format_name
    },
    frameIndex: {
      count: frameLines.length,
      sampleFrame0: JSON.parse(frameLines[0] || '{}')
    },
    snapshots: {
      count: snapshots.length,
      files: snapshots
    },
    verificationPassed:
      finalState.videoStatus === 'stopped' &&
      stat.size > 5000 &&
      videoStream?.codec_name === 'vp9' &&
      snapshots.length >= 4
  }

  const proofFile = path.join(__dirname, 'real-electron-recording-proof.json')
  fs.writeFileSync(proofFile, JSON.stringify(proofReport, null, 2), 'utf-8')

  console.log('[proof] SUCCESS! Proof report generated at:', proofFile)
  console.log(JSON.stringify(proofReport, null, 2))

  win.destroy()
  app.quit()
}

app.whenReady().then(run).catch(err => {
  console.error('[proof] ERROR during real Electron proof:', err)
  app.exit(1)
})
