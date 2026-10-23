// site-ops/framework/selector-resolver.mjs
// Selector Resolver — Priority-based selector lookup and element discovery in site maps.

export function getScreenElements(map, screenName = 'main') {
  if (!map || !map.screens) return []
  const screen = map.screens[screenName]
  return screen?.elements || []
}

function findInScreens(map, predicate, returnAll = false) {
  if (!map || !map.screens) return returnAll ? [] : null
  const results = []
  for (const [screenName, screen] of Object.entries(map.screens || {})) {
    for (const el of screen.elements || []) {
      if (predicate(el)) {
        if (!returnAll) return { ...el, screen: screenName }
        results.push({ ...el, screen: screenName })
      }
    }
  }
  return returnAll ? results : null
}

export function buildSelector(element) {
  if (!element) return ''
  if (element.testId) {
    return `[data-testid="${element.testId}"]`
  }
  if (element.ariaLabel) {
    const tag = element.tag || '*'
    return `${tag}[aria-label="${element.ariaLabel.replace(/"/g, '\\"')}"]`
  }
  if (element.id) {
    return `#${element.id}`
  }
  if (element.role) {
    const tag = element.tag || '*'
    return `${tag}[role="${element.role}"]`
  }
  if (element.text && element.text.length < 60 && element.text.length > 0) {
    const tag = element.tag || '*'
    return `${tag}:has-text("${element.text.replace(/"/g, '\\"').substring(0, 40)}")`
  }
  if (element.selector) {
    return element.selector
  }
  return ''
}

export const resolveSelector = buildSelector

export function findElement(map, findersOrPredicate, screenName = 'main') {
  if (typeof findersOrPredicate === 'function') {
    const elements = getScreenElements(map, screenName)
    const match = elements.find(findersOrPredicate)
    if (match) return match
    return findInScreens(map, findersOrPredicate, false)
  }
  if (Array.isArray(findersOrPredicate)) {
    for (const fn of findersOrPredicate) {
      const result = fn(map)
      if (result) return result
    }
  }
  return null
}

export function findElements(map, predicate, screenName = 'main') {
  const elements = getScreenElements(map, screenName)
  return elements.filter(predicate)
}

export function findElementByTestId(map, testId) {
  return findInScreens(map, el => el.testId === testId)
}
export const findByTestId = findElementByTestId

export function findElementByAriaLabel(map, ariaLabel, options = {}) {
  const { exact = false, includes = false } = options
  return findInScreens(map, el => {
    if (!el.ariaLabel) return false
    if (exact) return el.ariaLabel === ariaLabel
    if (includes) return el.ariaLabel.includes(ariaLabel)
    return el.ariaLabel === ariaLabel || el.ariaLabel.includes(ariaLabel)
  })
}
export const findByAriaLabel = findElementByAriaLabel

export function findElementByPlaceholder(map, placeholder, options = {}) {
  const { exact = false, includes = false } = options
  return findInScreens(map, el => {
    if (!el.placeholder) return false
    if (exact) return el.placeholder === placeholder
    if (includes) return el.placeholder.includes(placeholder)
    return el.placeholder === placeholder || el.placeholder.includes(placeholder)
  })
}
export const findByPlaceholder = findElementByPlaceholder

export function findElementByRole(map, role) {
  return findInScreens(map, el => el.role === role)
}
export const findByRole = findElementByRole

export function findElementByText(map, text, options = {}) {
  const { includes = false, maxLength = 80 } = options
  return findInScreens(map, el => {
    if (!el.text) return false
    const t = el.text.substring(0, maxLength)
    return includes ? t.includes(text) : t === text
  })
}
export const findByText = findElementByText

export function findElementByCategory(map, category) {
  return findInScreens(map, el => el.category === category)
}

export function findNavTriggers(map) {
  return findInScreens(map, el => el.isNavTrigger === true, true)
}

export function findInputElement(map) {
  return findElement(map, [
    m => findElementByRole(m, 'textbox'),
    m => findElementByCategory(m, 'input'),
    m => findInScreens(m, el => el.contentEditable === 'true')
  ])
}

export function findSearchInput(map) {
  return findElement(map, [
    m => findElementByAriaLabel(m, 'Search', { includes: true }),
    m => findElementByPlaceholder(m, 'Search', { includes: true }),
    m => findElementByTestId(m, 'search-input'),
    m => findElementByTestId(m, 'search'),
  ])
}

export function findMessageInput(map) {
  return findElement(map, [
    m => findElementByAriaLabel(m, 'Type a message', { exact: true }),
    m => findElementByRole(m, 'textbox'),
    m => findElementByTestId(m, 'message-input'),
    m => findElementByTestId(m, 'composer'),
  ])
}
