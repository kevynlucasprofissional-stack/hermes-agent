import { describe, expect, it } from 'vitest'

import { type SafeHumanBrowserGesture } from './workstation-learning-events'
import {
  detectSemanticCategory,
  LearningDemonstrationSegmenter
} from './workstation-learning-segmenter'

function makeGesture(
  overrides: Partial<SafeHumanBrowserGesture> = {}
): SafeHumanBrowserGesture {
  return {
    schema: 'hermes.human_gesture.v1',
    event_id: `ev-${Math.random().toString(36).slice(2, 7)}`,
    browser_tab_id: 'tab-test',
    document_epoch: 'epoch-1',
    time_ms: 1000,
    kind: 'click',
    actor: 'human',
    ...overrides
  }
}

describe('LearningDemonstrationSegmenter', () => {
  it('detects semantic categories accurately from gestures', () => {
    const importClick = makeGesture({
      target: { role: 'button', accessible_name: 'Importar Imagem' }
    })
    expect(detectSemanticCategory(importClick).kind).toBe('asset_import')

    const stampClick = makeGesture({
      target: { role: 'button', accessible_name: 'Ferramenta Carimbo' }
    })
    const stampRes = detectSemanticCategory(stampClick)
    expect(stampRes.kind).toBe('tool_selection')
    expect(stampRes.toolName).toBe('carimbo')

    const canvasPointer = makeGesture({
      kind: 'pointerdown',
      normalized_position: { x: 0.5, y: 0.5 }
    })
    expect(detectSemanticCategory(canvasPointer).kind).toBe('canvas_operation')

    const textClick = makeGesture({
      target: { role: 'button', accessible_name: 'Texto e Fonte' }
    })
    expect(detectSemanticCategory(textClick).kind).toBe('typography_adjustment')
  })

  it('groups multiple canvas strokes under active tool in a single segment', () => {
    const segmenter = new LearningDemonstrationSegmenter('sess-1', 'tab-1')

    // 1. Select stamp tool
    segmenter.addGesture(makeGesture({
      time_ms: 1000,
      target: { role: 'button', accessible_name: 'Ferramenta de Carimbo' }
    }))

    // 2. Three canvas strokes in sequence
    segmenter.addGesture(makeGesture({
      time_ms: 1500,
      kind: 'pointerdown',
      normalized_position: { x: 0.1, y: 0.2 }
    }))
    segmenter.addGesture(makeGesture({
      time_ms: 2000,
      kind: 'pointerup',
      normalized_position: { x: 0.1, y: 0.2 }
    }))
    segmenter.addGesture(makeGesture({
      time_ms: 2500,
      kind: 'pointerup',
      normalized_position: { x: 0.12, y: 0.22 }
    }))

    const segments = segmenter.getSegments()
    expect(segments.length).toBe(2) // 1 tool selection, 1 canvas operation segment
    const canvasSeg = segments[1]
    expect(canvasSeg.kind).toBe('canvas_operation')
    expect(canvasSeg.observableContext.activeTool).toBe('carimbo')
    expect(canvasSeg.observableContext.strokeCount).toBe(3)
    expect(canvasSeg.hypothesis).toContain("ferramenta 'carimbo'")
    expect(canvasSeg.hypothesis).toContain('3 intervenções no canvas')
  })

  it('creates new segment on temporal pause exceeding threshold', () => {
    const segmenter = new LearningDemonstrationSegmenter('sess-1', 'tab-1', 4000)

    segmenter.addGesture(makeGesture({ time_ms: 1000, kind: 'click', target: { role: 'button', accessible_name: 'Crop' } }))
    segmenter.addGesture(makeGesture({ time_ms: 2000, kind: 'click', target: { role: 'button', accessible_name: 'Crop' } }))

    // Pause of 6 seconds (> 4s threshold)
    segmenter.addGesture(makeGesture({ time_ms: 8500, kind: 'click', target: { role: 'button', accessible_name: 'Crop' } }))

    expect(segmenter.getSegments().length).toBe(2)
  })

  it('formulates causality and alternative questions instead of coordinates', () => {
    const segmenter = new LearningDemonstrationSegmenter('sess-1', 'tab-1')

    // Tool switch to stamp
    segmenter.addGesture(makeGesture({
      time_ms: 1000,
      target: { role: 'button', accessible_name: 'Clone Stamp' }
    }))

    const qTool = segmenter.generateQuestionCandidate(1100)
    expect(qTool?.category).toBe('causality')
    expect(qTool?.proposedQuestion).toContain("ferramenta 'carimbo'")

    // Canvas operation with stamp
    segmenter.addGesture(makeGesture({
      time_ms: 1500,
      kind: 'pointerup',
      normalized_position: { x: 0.8, y: 0.6 }
    }))

    const qCanvas = segmenter.generateQuestionCandidate(1600)
    expect(qCanvas?.category).toBe('alternative')
    expect(qCanvas?.proposedQuestion).toContain("Você considerou ou testou outra técnica antes de aplicar 'carimbo'")
    expect(qCanvas?.proposedQuestion).not.toContain('0.8')
    expect(qCanvas?.proposedQuestion).not.toContain('0.6')
  })

  it('applies human correction with precedence and suppresses already explained topics', () => {
    const segmenter = new LearningDemonstrationSegmenter('sess-1', 'tab-1')

    segmenter.addGesture(makeGesture({
      time_ms: 1000,
      target: { role: 'button', accessible_name: 'Importar Imagem' }
    }))

    const q = segmenter.generateQuestionCandidate(1100)
    expect(q).not.toBeNull()
    expect(q?.category).toBe('intent')

    // Operator provides causal correction
    segmenter.recordHumanAnswer(
      q!.policyCandidate.id,
      q!.proposedQuestion,
      'Importei uma imagem que vou editar',
      true
    )

    const segments = segmenter.getSegments()
    expect(segments[0].hypothesis).toBe('[Correção do operador] Importei uma imagem que vou editar')
    expect(segments[0].uncertainty).toBe(0.05)
    expect(segments[0].humanCorrections.length).toBe(1)
    expect(segments[0].humanCorrections[0].needsReinterpretation).toBe(true)

    // A subsequent question on the same topic must be suppressed
    const qNext = segmenter.generateQuestionCandidate(1200)
    expect(qNext).toBeNull()
  })

  it('informs absence of autonomous interpretation without provider', () => {
    const segmenter = new LearningDemonstrationSegmenter('sess-1', 'tab-1')

    // Canvas click without known tool and without provider
    segmenter.addGesture(makeGesture({
      time_ms: 1000,
      kind: 'pointerup',
      normalized_position: { x: 0.25, y: 0.75 }
    }))

    const candidate = segmenter.generateQuestionCandidate(1100, false)
    expect(candidate).not.toBeNull()
    expect(candidate?.hypothesis).toContain('Ausência de interpretação autônoma')
    expect(candidate?.policyCandidate.uncertainty).toBe(0.9)
    expect(candidate?.proposedQuestion).toContain('Qual foi o objetivo desta intervenção manual no Canvas?')
    // Does NOT invent fake clicks or coordinates templates
    expect(candidate?.hypothesis).not.toContain('(0.25, 0.75)')
  })

  it('builds complete demonstration package with structured evidence references', () => {
    const segmenter = new LearningDemonstrationSegmenter('sess-demo', 'tab-demo')

    segmenter.addGesture(makeGesture({
      time_ms: 1000,
      target: { role: 'button', accessible_name: 'Novo Documento 1080x1440' }
    }))

    const pkg = segmenter.buildDemonstrationPackage(
      'http://127.0.0.1:8767',
      '2026-10-18T12:00:00Z',
      '2026-10-18T12:05:00Z',
      15,
      2,
      'C:/test/sess-demo',
      'lesson_hd_123'
    )

    expect(pkg.schema).toBe('hermes.demonstration_package.v1')
    expect(pkg.sessionId).toBe('sess-demo')
    expect(pkg.segmentsCount).toBe(1)
    expect(pkg.candidateLessonId).toBe('lesson_hd_123')
    expect(pkg.compilationStatus).toBe('compiled')
    expect(pkg.evidenceRefs.eventsPath).toContain('events.jsonl')
    expect(pkg.limitations.length).toBeGreaterThan(0)
    expect(pkg.limitations[0]).toContain('Não validada em tempo de execução')
  })

  it('incorporates container breadcrumbs and control values in hypotheses and questions (P05)', () => {
    const segmenter = new LearningDemonstrationSegmenter('sess-1', 'tab-1')

    segmenter.addGesture(makeGesture({
      time_ms: 1000,
      target: {
        role: 'slider',
        accessible_name: 'Opacidade',
        containerBreadcrumb: 'Painel de Camadas',
        currentValue: '35%',
        unit: '%'
      }
    }))

    const candidate = segmenter.generateQuestionCandidate(1100)
    expect(candidate).not.toBeNull()
    expect(candidate?.category).toBe('causality')
    expect(candidate?.hypothesis).toBe("O operador ajustou 'Opacidade' para 35% no Painel de Camadas.")
    expect(candidate?.proposedQuestion).toBe('Qual critério visual determinou o ajuste de opacidade para 35% no painel de camadas?')
  })

  it('formulates causality questions on modal opened mutation delta (P05)', () => {
    const segmenter = new LearningDemonstrationSegmenter('sess-1', 'tab-1')

    segmenter.addGesture(makeGesture({
      time_ms: 1000,
      target: {
        role: 'button',
        accessible_name: 'Opções de Mesclagem'
      },
      domDelta: {
        effectKind: 'modal_opened',
        summary: 'Diálogo de opções aberto'
      }
    }))

    const candidate = segmenter.generateQuestionCandidate(1100)
    expect(candidate).not.toBeNull()
    expect(candidate?.category).toBe('causality')
    expect(candidate?.hypothesis).toContain("O operador acessou a janela de opções de 'Opções de Mesclagem'")
    expect(candidate?.proposedQuestion).toBe('Por que você acessou as opções de mesclagem nesta etapa da composição?')
  })

  it('correlates panel parameters and active tool with canvas interactions (P05)', () => {
    const segmenter = new LearningDemonstrationSegmenter('sess-1', 'tab-1')

    // 1. Select brush tool
    segmenter.addGesture(makeGesture({
      time_ms: 1000,
      target: { role: 'button', accessible_name: 'Pincel' }
    }))

    // 2. Adjust opacity in layer panel
    segmenter.addGesture(makeGesture({
      time_ms: 1500,
      target: {
        role: 'slider',
        accessible_name: 'Opacidade',
        containerBreadcrumb: 'Painel de Camadas',
        currentValue: '35%'
      }
    }))

    // 3. Draw on canvas
    segmenter.addGesture(makeGesture({
      time_ms: 2000,
      kind: 'pointerdown',
      normalized_position: { x: 0.4, y: 0.4 }
    }))
    segmenter.addGesture(makeGesture({
      time_ms: 2200,
      kind: 'pointerup',
      normalized_position: { x: 0.45, y: 0.45 }
    }))

    const segments = segmenter.getSegments()
    const canvasSeg = segments[segments.length - 1]
    expect(canvasSeg.kind).toBe('canvas_operation')
    expect(canvasSeg.hypothesis).toContain("ferramenta 'pincel'")
    expect(canvasSeg.hypothesis).toContain('Painel de Camadas')

    const candidate = segmenter.generateQuestionCandidate(2300)
    expect(candidate).not.toBeNull()
    expect(candidate?.category).toBe('alternative')
    expect(candidate?.proposedQuestion).toContain("Qual critério determinou o uso de 'pincel' com opacidade em 35% ajustado no painel de camadas para esta área do Canvas?")
  })

  it('triggers segment boundary when moving between distinct container panels (P05)', () => {
    const segmenter = new LearningDemonstrationSegmenter('sess-1', 'tab-1')

    segmenter.addGesture(makeGesture({
      time_ms: 1000,
      target: {
        role: 'button',
        accessible_name: 'Nova Camada',
        containerBreadcrumb: 'Painel de Camadas'
      }
    }))

    segmenter.addGesture(makeGesture({
      time_ms: 1200,
      target: {
        role: 'button',
        accessible_name: 'Aplicar Desfoque',
        containerBreadcrumb: 'Painel de Filtros'
      }
    }))

    expect(segmenter.getSegments().length).toBe(2)
  })
})
