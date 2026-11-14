#!/usr/bin/env python3
"""Append-only documentation merge, explicitly approved by maintainer, 2026-10-27."""
from pathlib import Path
ROOT=Path(r'C:\Github\hermes-agent')
KIT=ROOT/'workstation/context/hermes-implementation-kit-2026-10-26'
MAP={
 'updates/ROADMAP.md':'workstation/ROADMAP.md',
 'updates/HERMES_WORKSTATION_INTELLIGENCE.md':'workstation/context/HERMES_WORKSTATION_INTELLIGENCE.md',
 'updates/engineering-journal-CURRENT.md':'workstation/context/engineering-journal/CURRENT.md',
 'updates/DECISIONS.md':'workstation/context/DECISIONS.md',
 'updates/KNOWN_ISSUES.md':'workstation/context/KNOWN_ISSUES.md',
}
MARKER='<!-- HERMES-WORK-P01-20261027-MAINTAINER-WAIVER -->'
PLANMARK='<!-- HERMES-WORK-PLAN-20261026:PLAN_ONLY -->'
DETAILS={
 'workstation/ROADMAP.md': '''
## 2026-10-27 — HW-IMP-01: LOCAL_IMPLEMENTED / RELEASE_HOLD
O mantenedor autorizou explicitamente pular H-079 para desenvolvimento local, não release.
Upload nativo CDP agora passa pelo gate mutating/guarded, escopo explícito de roots por TaskRun no config.yaml, readback local e receipt persistido. Testes focalizados GREEN, Electron CDP fixture offline PASS; regressão ampla contém 28 falhas em teste antigo com mock app.getAppPath ausente. Não promover até corrigir/verificar baseline e teste E2E do runtime real.
''',
 'workstation/context/HERMES_WORKSTATION_INTELLIGENCE.md': '''
## 2026-10-27 — Upload nativo por CDP: limites de autoridade
browser_file_upload é uma mutação: evento change pode iniciar upload de rede pelo site.
A autorização vem apenas do config.yaml do perfil ativo, campo browser.workstation.upload_grants (task_id, session_id, run_id, expires_at, allowed_roots, max_bytes/max_files opcionais), nunca dos argumentos controlados pelo modelo. Escopo ausente falha fechado. Proteção contra agente com escrita direta em config.yaml não é demonstrada: risco residual. Resultado selected não equivale a envio remoto confirmado, e não autoriza WhatsApp.
''',
 'workstation/context/engineering-journal/CURRENT.md': '''
## 2026-10-27 — HW-IMP-01 execução local autorizada (SEM RELEASE)
Mantenedor dispensou H-079 para esta implementação local e autorizou preservar/editar WIP na main sem operações destrutivas Git. Baseline HEAD f1d5ab2f030e940ed4571371b0de45a21a009c9e.
Testes RED comprovados: helper 4 falhas comportamentais; runtime 3 falhas. GREEN: helper 4/4; runtime 3/3. Suite electron maior 36 PASS e 28 FAIL por mock de app.getAppPath em workstation-browser-runtime-task.test.ts. Typecheck 0. Electron Chromium 144 fixture data: offline selecionou um arquivo real, FileList count 1, evento change 1, exit 0. Não houve envio externo, commit, push ou release.
''',
 'workstation/context/DECISIONS.md': '''
## D-20261027-P01 — Waiver pontual e CDP seguro
Mantenedor autorizou pular H-079 exclusivamente para trabalhar no estado local atual. Não alterou o gate de release, leases humanos, incerteza ou autoridade da TaskRun. A solução usa Chromium/Electron existente, valida realpath/arquivos/roots com grant expresso do operador por TaskRun no config.yaml, admission/receipt persistentes e resposta sem caminhos absolutos. Nenhum subsistema paralelo ou envio WhatsApp.
''',
 'workstation/context/KNOWN_ISSUES.md': '''
## HW-UPLOAD-01 — 2026-10-27, LOCAL FIX / QUALIFICATION HOLD
Mitigações locais: browser_file_upload incluído nos gates de mutação e admission; escopo por TaskRun no config.yaml, validação realpath/arquivo regular/tamanho/raiz, DOM único e input file, readback CDP e receipt. Falta qualificação E2E do próprio runtime em Electron real e revisão de autoridade contra eventual edição indevida da configuração. Suite grande registra 28 falhas de mock app.getAppPath, a investigar sem atribuir causalidade. Falha original em symlink Windows no setup EPERM, teste junction alternativo passou. WA-M3-01 e HLM-M3 continuam HOLD, sem release.
'''
}
for source,dest in MAP.items():
    target=ROOT/dest
    raw=target.read_bytes()
    if MARKER.encode('utf-8') in raw:
        print('SKIP_ALREADY_APPLIED',dest)
        continue
    newline='\r\n' if b'\r\n' in raw else '\n'
    appendix=''
    if PLANMARK.encode('utf-8') not in raw:
        appendix+='\n\n'+PLANMARK+'\n\n'+(KIT/source).read_text(encoding='utf-8').strip()+'\n'
    appendix+='\n'+MARKER+'\n'+DETAILS[dest].strip()+'\n'
    with target.open('ab') as f:
        f.write(appendix.replace('\n',newline).encode('utf-8'))
    print('APPENDED',dest)
