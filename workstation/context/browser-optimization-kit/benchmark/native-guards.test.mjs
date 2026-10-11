import assert from 'node:assert/strict'
import { mkdtemp, mkdir, rm, symlink, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import path from 'node:path'
import test from 'node:test'

import { canonicalPath, findElement, fixtureUrl, inside, resolveRunPaths, resolveTestHome } from './native-guards.mjs'

test('containment uses path segments and handles Windows drives', () => {
  for (const [child, expected] of [
    ['/kit/home', true], ['/kit/home/output/result.jsonl', true], ['/kit/home/..cache/result', true],
    ['/kit/home-other/result', false], ['/kit/home/../result', false], ['/elsewhere/result', false]
  ]) assert.equal(inside('/kit/home', child, path.posix), expected, child)
  for (const [child, expected] of [
    ['C:\\kit\\home', true], ['C:\\kit\\home\\..cache\\result', true],
    ['C:\\kit\\home-other\\result', false], ['C:\\kit\\home\\..\\result', false],
    ['D:\\kit\\home\\result', false], ['\\\\server\\share\\result', false]
  ]) assert.equal(inside('C:\\kit\\home', child, path.win32), expected, child)
})

async function temporaryPaths(t) {
  const root = await mkdtemp(path.join(tmpdir(), 'brow01-guards-'))
  t.after(() => rm(root, { recursive: true, force: true }))
  const testHome = path.join(root, 'isolated')
  const defaultHome = path.join(root, 'fake-default')
  const outside = path.join(root, 'outside')
  await Promise.all([testHome, defaultHome, outside].map(value => mkdir(value, { recursive: true })))
  const controllerFile = path.join(testHome, 'workstation', 'Runtime', 'browser-control.json')
  await mkdir(path.dirname(controllerFile), { recursive: true })
  await writeFile(controllerFile, '{}')
  return { root, testHome, defaultHome, outside, controllerFile }
}

async function directoryLink(t, target, link) {
  try {
    await symlink(target, link, process.platform === 'win32' ? 'junction' : 'dir')
    return true
  } catch (error) {
    if (!['EPERM', 'EACCES', 'ENOSYS', 'ENOTSUP'].includes(error.code)) throw error
    t.skip(`directory links unavailable: ${error.code}`)
    return false
  }
}

test('run paths canonicalize missing output ancestors and reject lexical escapes', async t => {
  const paths = await temporaryPaths(t)
  const output = path.join(paths.testHome, '..cache', 'new', 'samples.jsonl')
  const actual = await resolveRunPaths({ ...paths, output })
  assert.equal(actual.testHome, await canonicalPath(paths.testHome))
  assert.equal(actual.output, path.join(actual.testHome, '..cache', 'new', 'samples.jsonl'))
  await assert.rejects(resolveRunPaths({ ...paths, output: path.join(paths.root, 'isolated-other', 'samples.jsonl') }), /output must stay/)
  await assert.rejects(resolveTestHome(path.join(paths.defaultHome, 'nested'), paths.defaultHome), /default/)
  await assert.rejects(resolveRunPaths({ ...paths, output, controllerFile: path.join(paths.outside, 'browser-control.json') }), /descriptor inside/)
})

test('a home junction cannot alias the default home', async t => {
  const paths = await temporaryPaths(t)
  const alias = path.join(paths.root, 'default-alias')
  if (!await directoryLink(t, paths.defaultHome, alias)) return
  await assert.rejects(resolveTestHome(path.join(alias, 'new-home'), paths.defaultHome), /default/)
})

test('a missing output beneath an escaping directory link is rejected', async t => {
  const paths = await temporaryPaths(t)
  const linkedOutput = path.join(paths.testHome, 'linked-output')
  if (!await directoryLink(t, paths.outside, linkedOutput)) return
  await assert.rejects(resolveRunPaths({ ...paths, output: path.join(linkedOutput, 'new', 'samples.jsonl') }), /output must stay/)
})

test('the controller descriptor cannot escape through a directory link', async t => {
  const paths = await temporaryPaths(t)
  const runtime = path.join(paths.testHome, 'workstation', 'Runtime')
  await rm(runtime, { recursive: true })
  await writeFile(path.join(paths.outside, 'browser-control.json'), '{}')
  if (!await directoryLink(t, paths.outside, runtime)) return
  await assert.rejects(resolveRunPaths({ ...paths, output: path.join(paths.testHome, 'samples.jsonl') }), /descriptor inside/)
})

test('snapshot lookup consumes the controller result envelope directly', () => {
  const element = { testid: 'form-name', ref: 'actual-ref' }
  const body = { success: true, result: { elements: [element] } }
  assert.equal(findElement(body, 'form-name'), element)
  assert.equal(findElement(body, 'missing'), null)
  assert.equal(findElement({ result: body }, 'form-name'), null)
  assert.equal(findElement(undefined, 'form-name'), null)
})

test('fixture query parameters preserve the run identity and encode extras', () => {
  const config = { baseUrl: 'http://127.0.0.1:1234', runId: 'execução & run one' }
  const url = new URL(fixtureUrl(config, 'delayed-hydration', { delay_ms: 350, label: 'ação & café one' }))
  assert.equal(url.pathname, '/scenario/delayed-hydration')
  assert.equal(url.searchParams.get('run_id'), config.runId)
  assert.equal(url.searchParams.get('delay_ms'), '350')
  assert.equal(url.searchParams.get('label'), 'ação & café one')
  assert.equal([...url.searchParams].length, 3)
  assert.equal(new URL(fixtureUrl(config, 'lists-tables', { rows: 500 })).searchParams.get('rows'), '500')
})
