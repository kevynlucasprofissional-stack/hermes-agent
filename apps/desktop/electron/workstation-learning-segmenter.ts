/**
 * HLM-MVP Demonstration Segmenter and Contextual Question Engine (D-047 / P04).
 * Groups human gestures into temporal and causal segments, replaces coordinate-based
 * templates with intent/causality/alternative/validation questions, enforces human
 * correction precedence, and packages demonstration evidence for candidate compilation.
 */

import {
  type DomMutationDelta,
  type DomMutationEffectKind,
  type SafeHumanBrowserGesture,
  type SafeHumanBrowserGestureTarget
} from './workstation-learning-events'
import {
  type LearningQuestionCandidate,
  type LearningQuestionKind
} from './workstation-learning-question-policy'

export type DemonstrationSegmentKind =
  | 'document_setup'
  | 'asset_import'
  | 'tool_selection'
  | 'canvas_operation'
  | 'typography_adjustment'
  | 'parameter_adjustment'
  | 'generic'

export interface DemonstrationHumanCorrection {
  questionId: string
  prompt: string
  userResponse: string
  correctedAt: string
  needsReinterpretation: boolean
}

export interface DemonstrationSegment {
  id: string
  sessionId: string
  tabId: string
  segmentIndex: number
  eventRefs: string[]
  frameRefs: string[]
  fromMs: number
  toMs: number
  durationMs: number
  kind: DemonstrationSegmentKind
  observableContext: {
    activeTool?: string
    toolCategory?: string
    targetRole?: string
    targetName?: string
    containerBreadcrumb?: string
    currentValue?: string
    unit?: string
    effectKind?: DomMutationEffectKind
    domDelta?: DomMutationDelta
    lastParamAdjustment?: {
      targetName?: string
      value?: string
      container?: string
    }
    shortcut?: string
    canvasRegions?: Array<{ x: number; y: number }>
    strokeCount?: number
    pageUrl?: string
    pageTitle?: string
    summary?: string
  }
  hypothesis: string
  uncertainty: number
  humanCorrections: DemonstrationHumanCorrection[]
  status: 'active' | 'closed'
}

export interface ContextualCandidateResult {
  policyCandidate: LearningQuestionCandidate
  category: string
  hypothesis: string
  proposedQuestion: string
  segmentId: string
}

export interface DemonstrationPackage {
  schema: 'hermes.demonstration_package.v1'
  sessionId: string
  tabId: string
  origin: string
  startedAt: string
  endedAt: string
  eventsCount: number
  questionsCount: number
  segmentsCount: number
  segments: DemonstrationSegment[]
  evidenceRefs: {
    eventsPath: string
    questionsPath: string
    snapshotsDir: string
    mediaDir: string
    sessionDir: string
  }
  humanCorrections: DemonstrationHumanCorrection[]
  limitations: string[]
  compilationStatus: 'pending_compilation' | 'compiled' | 'none'
  candidateLessonId?: string
}

const DEFAULT_PAUSE_THRESHOLD_MS = 5_000

const TOOL_KEYWORDS: Array<{ match: RegExp; tool: string; category: string; kind: DemonstrationSegmentKind }> = [
  { match: /stamp|carimbo|clone/i, tool: 'carimbo', category: 'clone_stamp', kind: 'tool_selection' },
  { match: /fill|preenchimento|bucket|balde/i, tool: 'preenchimento', category: 'fill_bucket', kind: 'tool_selection' },
  { match: /text|texto|type|fonte|font|typography|tipografia/i, tool: 'texto', category: 'typography', kind: 'typography_adjustment' },
  { match: /brush|pincel|paint|desenho/i, tool: 'pincel', category: 'brush', kind: 'tool_selection' },
  { match: /select|selec|marquee|lasso|laço/i, tool: 'seleção', category: 'selection', kind: 'tool_selection' },
  { match: /eraser|borracha/i, tool: 'borracha', category: 'eraser', kind: 'tool_selection' },
  { match: /crop|cortar|recorte/i, tool: 'recorte', category: 'crop', kind: 'tool_selection' },
  { match: /filter|filtro|blur|desfoque|effect|efeito/i, tool: 'filtro', category: 'filter', kind: 'tool_selection' }
]

const SETUP_KEYWORDS = /new|novo|dimension|dimens|canvas size|tamanho|1080|1440|create|criar/i
const IMPORT_KEYWORDS = /import|importar|open|abrir|upload|carregar|file/i

function detectShortcutSemantic(shortcut: string): { kind: DemonstrationSegmentKind; actionName: string } | null {
  if (!shortcut) {return null}
  if (/ctrl\+n|meta\+n/i.test(shortcut)) {return { kind: 'document_setup', actionName: 'Novo documento' }}
  if (/ctrl\+o|meta\+o/i.test(shortcut)) {return { kind: 'asset_import', actionName: 'Importar arquivo' }}
  if (/ctrl\+s|meta\+s/i.test(shortcut)) {return { kind: 'parameter_adjustment', actionName: 'Salvar/Sincronizar' }}
  return null
}

function detectKeywordSemantic(combined: string): { kind: DemonstrationSegmentKind; toolName?: string; toolCategory?: string; actionName?: string } | null {
  if (SETUP_KEYWORDS.test(combined)) {
    return { kind: 'document_setup', actionName: 'Configurar documento' }
  }
  if (IMPORT_KEYWORDS.test(combined)) {
    return { kind: 'asset_import', actionName: 'Importar imagem/recurso' }
  }
  for (const item of TOOL_KEYWORDS) {
    if (item.match.test(combined)) {
      return { kind: item.kind, toolName: item.tool, toolCategory: item.category }
    }
  }
  return null
}

const PARAM_ROLES = new Set(['button', 'menuitem', 'combobox', 'switch', 'checkbox'])
const SLIDER_ROLES = new Set(['slider', 'spinbutton'])

function isPointerGesture(kind: string): boolean {
  return kind === 'pointerdown' || kind === 'pointerup'
}

function detectControlSemantic(
  role: string,
  target?: SafeHumanBrowserGestureTarget,
  accessibleName?: string
): { kind: DemonstrationSegmentKind; actionName?: string } | null {
  if (SLIDER_ROLES.has(role) || Boolean(target?.currentValue ?? target?.current_value)) {
    return { kind: 'parameter_adjustment', actionName: accessibleName || 'Ajuste de controle' }
  }
  if (PARAM_ROLES.has(role)) {
    return { kind: 'parameter_adjustment', actionName: accessibleName || role }
  }
  return null
}

export function detectSemanticCategory(gesture: SafeHumanBrowserGesture): {
  kind: DemonstrationSegmentKind
  toolName?: string
  toolCategory?: string
  actionName?: string
} {
  const accessibleName = gesture.target?.accessible_name || gesture.target?.accessibleName || ''
  const role = gesture.target?.role || ''

  if (gesture.kind === 'shortcut') {
    const sc = detectShortcutSemantic(gesture.shortcut || '')
    if (sc) {
      return sc
    }
  }

  const keywordMatch = detectKeywordSemantic(`${accessibleName} ${role}`.trim())
  if (keywordMatch) {
    if (accessibleName && !keywordMatch.toolName) {
      keywordMatch.actionName = accessibleName
    }
    return keywordMatch
  }

  if (isPointerGesture(gesture.kind)) {
    return { kind: 'canvas_operation' }
  }

  const controlSemantic = detectControlSemantic(role, gesture.target, accessibleName)
  if (controlSemantic) {
    return controlSemantic
  }

  return { kind: 'generic' }
}

export class LearningDemonstrationSegmenter {
  private segments: DemonstrationSegment[] = []
  private currentSegment: DemonstrationSegment | null = null
  private activeTool: string | null = null
  private lastParamAdjustment?: { targetName?: string; value?: string; container?: string }
  private explainedTopics = new Set<string>()
  private readonly pauseThresholdMs: number
  private readonly sessionId: string
  private readonly tabId: string

  constructor(sessionId: string, tabId: string, pauseThresholdMs = DEFAULT_PAUSE_THRESHOLD_MS) {
    this.sessionId = sessionId
    this.tabId = tabId
    this.pauseThresholdMs = pauseThresholdMs
  }

  private recordLastParamFromGesture(gesture: SafeHumanBrowserGesture): void {
    const target = gesture.target
    const targetName = target?.accessibleName || target?.accessible_name
    const containerBreadcrumb = target?.containerBreadcrumb || target?.container_breadcrumb
    const currentValue = target?.currentValue || target?.current_value

    if (containerBreadcrumb || currentValue) {
      this.lastParamAdjustment = {
        targetName: targetName || 'parâmetro',
        value: currentValue,
        container: containerBreadcrumb
      }
    }
  }

  private updateSegmentObservableContext(segment: DemonstrationSegment, gesture: SafeHumanBrowserGesture): void {
    const target = gesture.target
    const containerBreadcrumb = target?.containerBreadcrumb || target?.container_breadcrumb
    const currentValue = target?.currentValue || target?.current_value
    const unit = target?.unit || target?.valueUnit
    const delta = gesture.domDelta || gesture.dom_delta

    if (containerBreadcrumb && !segment.observableContext.containerBreadcrumb) {
      segment.observableContext.containerBreadcrumb = containerBreadcrumb
    }
    if (currentValue && !segment.observableContext.currentValue) {
      segment.observableContext.currentValue = currentValue
      segment.observableContext.unit = unit
    }
    if (delta && delta.effectKind && delta.effectKind !== 'none') {
      segment.observableContext.effectKind = delta.effectKind
      segment.observableContext.domDelta = delta
    }

    if (gesture.normalized_position) {
      if (!segment.observableContext.canvasRegions) {
        segment.observableContext.canvasRegions = []
      }
      segment.observableContext.canvasRegions.push(gesture.normalized_position)
      segment.observableContext.strokeCount = (segment.observableContext.strokeCount || 0) + 1
    }
  }

  addGesture(gesture: SafeHumanBrowserGesture, currentFrameRef?: string): DemonstrationSegment {
    const semantic = detectSemanticCategory(gesture)

    if (semantic.toolName) {
      this.activeTool = semantic.toolName
    }

    this.recordLastParamFromGesture(gesture)

    if (this.checkBoundary(gesture, semantic) && this.currentSegment) {
      this.closeCurrentSegment()
    }

    if (!this.currentSegment) {
      this.currentSegment = this.createSegment(gesture, semantic)
      this.segments.push(this.currentSegment)
    }

    this.currentSegment.eventRefs.push(gesture.event_id)
    this.currentSegment.toMs = gesture.time_ms
    this.currentSegment.durationMs = Math.max(0, this.currentSegment.toMs - this.currentSegment.fromMs)

    if (currentFrameRef && !this.currentSegment.frameRefs.includes(currentFrameRef)) {
      this.currentSegment.frameRefs.push(currentFrameRef)
    }

    this.updateSegmentObservableContext(this.currentSegment, gesture)
    this.updateSegmentHypothesis(this.currentSegment)

    return this.currentSegment
  }

  recordHumanAnswer(
    questionId: string,
    prompt: string,
    response: string,
    needsReinterpretation: boolean
  ): void {
    const correction: DemonstrationHumanCorrection = {
      questionId,
      prompt,
      userResponse: response,
      correctedAt: new Date().toISOString(),
      needsReinterpretation
    }

    const targetSegment = this.findSegmentForQuestion(questionId) || this.currentSegment

    if (targetSegment) {
      targetSegment.humanCorrections.push(correction)
      targetSegment.hypothesis = `[Correção do operador] ${response}`
      targetSegment.uncertainty = 0.05
    }

    // Mark topic as explained to prevent asking the operator the same question again
    if (targetSegment) {
      this.explainedTopics.add(targetSegment.kind)
      if (targetSegment.observableContext.activeTool) {
        this.explainedTopics.add(`tool:${targetSegment.observableContext.activeTool}`)
      }
    }
  }

  generateQuestionCandidate(
    nowMs: number,
    hasProvider = false
  ): ContextualCandidateResult | null {
    if (!this.currentSegment || this.currentSegment.eventRefs.length === 0) {
      return null
    }

    const seg = this.currentSegment

    // Precedence: if the segment already received human causal explanation, do not ask again
    if (seg.humanCorrections.length > 0) {
      return null
    }

    // Suppress if the underlying topic has already been clarified by the user
    if (this.explainedTopics.has(seg.kind)) {
      return null
    }
    if (seg.observableContext.activeTool && this.explainedTopics.has(`tool:${seg.observableContext.activeTool}`)) {
      return null
    }

    return this.formulateQuestionForSegment(seg, nowMs, hasProvider)
  }

  closeCurrentSegment(): void {
    if (this.currentSegment) {
      this.currentSegment.status = 'closed'
      this.currentSegment = null
    }
  }

  getSegments(): DemonstrationSegment[] {
    return [...this.segments]
  }

  getHumanCorrections(): DemonstrationHumanCorrection[] {
    return this.segments.flatMap(s => s.humanCorrections)
  }

  buildDemonstrationPackage(
    origin: string,
    startedAt: string,
    endedAt: string,
    eventsCount: number,
    questionsCount: number,
    sessionDir: string,
    candidateLessonId?: string
  ): DemonstrationPackage {
    this.closeCurrentSegment()

    return {
      schema: 'hermes.demonstration_package.v1',
      sessionId: this.sessionId,
      tabId: this.tabId,
      origin,
      startedAt,
      endedAt,
      eventsCount,
      questionsCount,
      segmentsCount: this.segments.length,
      segments: this.segments,
      evidenceRefs: {
        eventsPath: `${sessionDir}/events.jsonl`,
        questionsPath: `${sessionDir}/questions.jsonl`,
        snapshotsDir: `${sessionDir}/snapshots`,
        mediaDir: `${sessionDir}/media`,
        sessionDir
      },
      humanCorrections: this.getHumanCorrections(),
      limitations: [
        'Demonstração humana em observação. Não validada em tempo de execução.',
        'Proibida promoção automática ou atribuição de status VERIFIED_SUCCESS sem qualificação.'
      ],
      compilationStatus: candidateLessonId ? 'compiled' : 'pending_compilation',
      candidateLessonId
    }
  }

  private isPhaseOrToolBoundary(
    gesture: SafeHumanBrowserGesture,
    semantic: ReturnType<typeof detectSemanticCategory>
  ): boolean {
    if (!this.currentSegment) {return false}
    if (semantic.kind === 'document_setup' && this.currentSegment.kind !== 'document_setup') {return true}
    if (semantic.kind === 'asset_import' && this.currentSegment.kind !== 'asset_import') {return true}
    if (semantic.toolName && this.currentSegment.observableContext.activeTool && semantic.toolName !== this.currentSegment.observableContext.activeTool) {return true}

    const isCanvas = gesture.kind === 'pointerdown' || gesture.kind === 'pointerup'
    const isCurrentCanvas = this.currentSegment.kind === 'canvas_operation'
    if (isCanvas && !isCurrentCanvas && this.currentSegment.eventRefs.length > 0) {return true}
    if (!isCanvas && isCurrentCanvas) {return true}

    return false
  }

  private isContainerOrModalBoundary(gesture: SafeHumanBrowserGesture): boolean {
    if (!this.currentSegment) {return false}
    const newContainer = gesture.target?.containerBreadcrumb || gesture.target?.container_breadcrumb
    const curContainer = this.currentSegment.observableContext.containerBreadcrumb
    if (newContainer && curContainer && newContainer !== curContainer) {return true}
    const delta = gesture.domDelta || gesture.dom_delta

    return delta?.effectKind === 'modal_opened'
  }

  private checkBoundary(
    gesture: SafeHumanBrowserGesture,
    semantic: ReturnType<typeof detectSemanticCategory>
  ): boolean {
    if (!this.currentSegment) {return false}
    if (gesture.time_ms - this.currentSegment.toMs > this.pauseThresholdMs) {return true}
    if (this.isPhaseOrToolBoundary(gesture, semantic)) {return true}

    return this.isContainerOrModalBoundary(gesture)
  }

  private createSegment(
    gesture: SafeHumanBrowserGesture,
    semantic: ReturnType<typeof detectSemanticCategory>
  ): DemonstrationSegment {
    const segmentIndex = this.segments.length
    const id = `seg-${segmentIndex + 1}-${gesture.event_id}`

    let kind = semantic.kind
    if (kind === 'generic' && (gesture.kind === 'pointerdown' || gesture.kind === 'pointerup')) {
      kind = 'canvas_operation'
    }

    const targetName = gesture.target?.accessibleName || gesture.target?.accessible_name
    const containerBreadcrumb = gesture.target?.containerBreadcrumb || gesture.target?.container_breadcrumb
    const currentValue = gesture.target?.currentValue || gesture.target?.current_value
    const unit = gesture.target?.unit || gesture.target?.valueUnit
    const delta = gesture.domDelta || gesture.dom_delta

    return {
      id,
      sessionId: this.sessionId,
      tabId: this.tabId,
      segmentIndex,
      eventRefs: [],
      frameRefs: [],
      fromMs: gesture.time_ms,
      toMs: gesture.time_ms,
      durationMs: 0,
      kind,
      observableContext: {
        activeTool: this.activeTool || semantic.toolName,
        toolCategory: semantic.toolCategory,
        targetRole: gesture.target?.role,
        targetName,
        containerBreadcrumb,
        currentValue,
        unit,
        effectKind: delta?.effectKind,
        domDelta: delta,
        lastParamAdjustment: kind === 'canvas_operation' ? this.lastParamAdjustment : undefined,
        shortcut: gesture.shortcut
      },
      hypothesis: 'Observando sequência de operações...',
      uncertainty: 0.8,
      humanCorrections: [],
      status: 'active'
    }
  }

  private buildCanvasHypothesis(segment: DemonstrationSegment): { hypothesis: string; uncertainty: number } {
    const tool = segment.observableContext.activeTool
    const strokes = segment.observableContext.strokeCount || 0
    const lastParam = segment.observableContext.lastParamAdjustment

    if (tool && lastParam?.container) {
      const paramDesc = lastParam.targetName && lastParam.value
        ? `${lastParam.targetName} (${lastParam.value}) no ${lastParam.container}`
        : lastParam.container

      return {
        hypothesis: `O operador aplicou a ferramenta '${tool}' (após ajuste de ${paramDesc}) em ${strokes} intervenções no canvas.`,
        uncertainty: 0.45
      }
    }
    if (tool) {
      return {
        hypothesis: `O operador aplicou a ferramenta '${tool}' em ${strokes} intervenções no canvas.`,
        uncertainty: 0.5
      }
    }

    return {
      hypothesis: `O operador realizou ${strokes} intervenções manuais no canvas.`,
      uncertainty: 0.85
    }
  }

  private buildParameterHypothesis(segment: DemonstrationSegment): { hypothesis: string; uncertainty: number } {
    const target = segment.observableContext.targetName
    const val = segment.observableContext.currentValue
    const container = segment.observableContext.containerBreadcrumb

    if (target && val && container) {
      return { hypothesis: `O operador ajustou '${target}' para ${val} no ${container}.`, uncertainty: 0.3 }
    }
    if (target && val) {
      return { hypothesis: `O operador ajustou '${target}' para ${val} na interface.`, uncertainty: 0.35 }
    }
    if (container) {
      return { hypothesis: `O operador realizou ajustes no ${container}.`, uncertainty: 0.4 }
    }
    if (segment.observableContext.shortcut) {
      return {
        hypothesis: `O operador executou o comando ou atalho '${segment.observableContext.shortcut}' durante a operação.`,
        uncertainty: 0.5
      }
    }

    return { hypothesis: 'O operador ajustou parâmetros na interface.', uncertainty: 0.5 }
  }

  private updateSegmentHypothesis(segment: DemonstrationSegment): void {
    if (segment.humanCorrections.length > 0) {
      return
    }

    const tool = segment.observableContext.activeTool
    const container = segment.observableContext.containerBreadcrumb
    const target = segment.observableContext.targetName
    const effect = segment.observableContext.effectKind

    if (effect === 'modal_opened') {
      segment.hypothesis = container
        ? `O operador abriu as opções de '${target || 'diálogo'}' no ${container}.`
        : `O operador acessou a janela de opções de '${target || 'diálogo'}' na composição.`
      segment.uncertainty = 0.35
      return
    }

    if (segment.kind === 'canvas_operation') {
      const res = this.buildCanvasHypothesis(segment)
      segment.hypothesis = res.hypothesis
      segment.uncertainty = res.uncertainty
      return
    }

    if (segment.kind === 'parameter_adjustment') {
      const res = this.buildParameterHypothesis(segment)
      segment.hypothesis = res.hypothesis
      segment.uncertainty = res.uncertainty
      return
    }

    if (segment.kind === 'document_setup') {
      segment.hypothesis = 'O operador configurou os parâmetros iniciais da área de trabalho ou dimensões do documento.'
      segment.uncertainty = 0.4
    } else if (segment.kind === 'asset_import') {
      segment.hypothesis = 'O operador importou uma imagem ou recurso externo para a composição.'
      segment.uncertainty = 0.35
    } else if (segment.kind === 'tool_selection') {
      segment.hypothesis = tool
        ? `O operador selecionou a ferramenta '${tool}' para manipulação específica na arte.`
        : 'O operador alternou ferramentas de edição na interface.'
      segment.uncertainty = 0.45
    } else if (segment.kind === 'typography_adjustment') {
      segment.hypothesis = 'O operador realizou ajustes tipográficos para aproximar estilo, texto ou fonte.'
      segment.uncertainty = 0.4
    } else {
      segment.hypothesis = 'O operador executou comandos ou ações na interface.'
      segment.uncertainty = 0.7
    }
  }

  private buildParameterQuestion(seg: DemonstrationSegment): string {
    const target = seg.observableContext.targetName
    const val = seg.observableContext.currentValue
    const container = seg.observableContext.containerBreadcrumb

    if (target && val && container) {
      return `Qual critério visual determinou o ajuste de ${target.toLowerCase()} para ${val} no ${container.toLowerCase()}?`
    }
    if (target && val) {
      return `Qual critério visual determinou o ajuste de ${target.toLowerCase()} para ${val}?`
    }
    if (container) {
      return `Qual foi o critério ou objetivo deste ajuste no ${container.toLowerCase()}?`
    }
    if (seg.observableContext.shortcut) {
      return `Por que você executou o atalho ${seg.observableContext.shortcut} nesta etapa da demonstração?`
    }

    return 'Qual foi o critério ou objetivo deste ajuste de parâmetro?'
  }

  private buildCanvasQuestion(
    seg: DemonstrationSegment,
    tool: string | undefined,
    hasProvider: boolean
  ): { kind: LearningQuestionKind; category: string; hypothesis?: string; proposedQuestion: string; uncertainty?: number } {
    const lastParam = seg.observableContext.lastParamAdjustment
    if (tool && lastParam?.container) {
      const paramDetail = lastParam.targetName && lastParam.value
        ? ` com ${lastParam.targetName.toLowerCase()} em ${lastParam.value}`
        : ''
      return {
        kind: 'alternative',
        category: 'alternative',
        proposedQuestion: `Qual critério determinou o uso de '${tool}'${paramDetail} ajustado no ${lastParam.container.toLowerCase()} para esta área do Canvas?`
      }
    }
    if (tool) {
      return {
        kind: 'alternative',
        category: 'alternative',
        proposedQuestion: `Você considerou ou testou outra técnica antes de aplicar '${tool}' nesta área?`
      }
    }
    if (hasProvider) {
      return {
        kind: 'intent',
        category: 'intent',
        proposedQuestion: 'Qual operação ou efeito visual você está aplicando nesta região do Canvas?'
      }
    }

    return {
      kind: 'intent',
      category: 'intent',
      hypothesis: 'Demonstração manual registrada. Ausência de interpretação autônoma sobre a operação de canvas sem sinal semântico.',
      proposedQuestion: 'Qual foi o objetivo desta intervenção manual no Canvas?',
      uncertainty: 0.9
    }
  }

  private buildSimpleSegmentQuestion(seg: DemonstrationSegment, tool: string | undefined): { kind: LearningQuestionKind; category: string; proposedQuestion: string } {
    if (seg.kind === 'document_setup') {
      return { kind: 'intent', category: 'intent', proposedQuestion: 'Qual é a especificação ou padrão desejado para as dimensões deste documento?' }
    }
    if (seg.kind === 'asset_import') {
      return { kind: 'intent', category: 'intent', proposedQuestion: 'Qual é a finalidade deste recurso importado no trabalho atual?' }
    }
    if (seg.kind === 'tool_selection') {
      return {
        kind: 'causality',
        category: 'causality',
        proposedQuestion: tool
          ? `Por que você optou por utilizar a ferramenta '${tool}' nesta etapa em vez de outra alternativa?`
          : 'Qual critério motivou a troca de ferramenta nesta etapa?'
      }
    }
    if (seg.kind === 'typography_adjustment') {
      return { kind: 'validation', category: 'validation', proposedQuestion: 'Qual critério você utilizou para validar se o ajuste tipográfico e a fonte ficaram adequados?' }
    }

    return { kind: 'intent', category: 'intent', proposedQuestion: 'Qual resultado você esperava alcançar com esta sequência de ações?' }
  }

  private formulateQuestionForSegment(
    seg: DemonstrationSegment,
    nowMs: number,
    hasProvider: boolean
  ): ContextualCandidateResult | null {
    const tool = seg.observableContext.activeTool
    const dedupeKey = `seg:${seg.kind}:${tool || 'notool'}:${seg.observableContext.containerBreadcrumb || 'nocontainer'}:${seg.observableContext.targetName || 'notarget'}:${seg.observableContext.effectKind || 'noeffect'}`

    let kind: LearningQuestionKind = 'intent'
    let category = 'intent'
    let hypothesis = seg.hypothesis
    let proposedQuestion = ''
    let novelty = 0.75
    let uncertainty = seg.uncertainty
    const reuseValue = 0.85
    const interruptionCost = 0.15

    if (seg.observableContext.effectKind === 'modal_opened') {
      kind = 'causality'
      category = 'causality'
      const target = seg.observableContext.targetName || 'diálogo'
      proposedQuestion = /mesclagem|blend/i.test(target)
        ? 'Por que você acessou as opções de mesclagem nesta etapa da composição?'
        : `Por que você acessou as opções de '${target}' nesta etapa da composição?`
    } else if (seg.kind === 'canvas_operation') {
      const q = this.buildCanvasQuestion(seg, tool, hasProvider)
      kind = q.kind
      category = q.category
      proposedQuestion = q.proposedQuestion
      if (q.hypothesis) {hypothesis = q.hypothesis}
      if (q.uncertainty !== undefined) {uncertainty = q.uncertainty}
    } else if (seg.kind === 'parameter_adjustment') {
      kind = 'causality'
      category = 'causality'
      proposedQuestion = this.buildParameterQuestion(seg)
    } else {
      const q = this.buildSimpleSegmentQuestion(seg, tool)
      kind = q.kind
      category = q.category
      proposedQuestion = q.proposedQuestion
    }

    const policyCandidate: LearningQuestionCandidate = {
      id: `cand-${seg.id}`,
      dedupeKey,
      kind,
      eventRefs: [...seg.eventRefs],
      novelty,
      uncertainty,
      reuseValue,
      interruptionCost
    }

    return {
      policyCandidate,
      category,
      hypothesis,
      proposedQuestion,
      segmentId: seg.id
    }
  }

  private findSegmentForQuestion(questionId: string): DemonstrationSegment | undefined {
    for (const seg of this.segments) {
      if (seg.humanCorrections.some(c => c.questionId === questionId)) {
        return seg
      }
    }

    return this.segments.length > 0 ? this.segments[this.segments.length - 1] : undefined
  }
}
