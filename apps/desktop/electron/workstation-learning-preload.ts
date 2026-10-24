import { ipcRenderer } from 'electron'

import {
  type LearningCaptureBinding,
  LEARNING_CAPTURE_CONTROL,
  LEARNING_CAPTURE_GESTURE
} from './workstation-learning-capture'
import { installLearningDomObserver } from './workstation-learning-dom'

if (process.isMainFrame) {
  let stopObserving: (() => void) | null = null

  const stop = (): void => {
    stopObserving?.()
    stopObserving = null
  }

  ipcRenderer.on(LEARNING_CAPTURE_CONTROL, (_event, binding: LearningCaptureBinding | null) => {
    stop()

    if (!binding || binding.origin !== location.origin) {
      return
    }

    stopObserving = installLearningDomObserver((gesture) => {
      ipcRenderer.send(LEARNING_CAPTURE_GESTURE, { binding, gesture })
    })
  })

  window.addEventListener('pagehide', stop)
}
