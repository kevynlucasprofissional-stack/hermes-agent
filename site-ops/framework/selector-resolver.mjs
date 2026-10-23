// Selector Resolver — Priority-based selector lookup in site maps
// Extracted from whatsapp-web.mjs

/**
 * Find element in site map using a predicate function.
 * Searches all screens and returns the first matching element.
 * 
 * @param {Object} map - Site map object with screens
 * @param {Function} predicate - Function(el) => boolean
 * @returns {Object|null} Matching element with selector, or null
 */
export function findElement(map, predicate) {
  for (const [screenName, screen] of Object.entries(map.screens || {})) {
    for (const el of screen.elements || []) {
      if (predicate(el)) {
        return { ...el, screen: screenName }
      }
    }
  }
  return null
}

/**
 * Build best CSS selector for an element based on available attributes.
 * Priority: data-testid > aria-label > id > role > text (short)
 * 
 * @param {Object} element - Element from site map
 * @returns {string} CSS selector
 */
export function resolveSelector(element) {
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
  return ''
}

export const buildSelector = resolveSelector


/**
 * High-level finders for common element types
 */

export function findInputElement(map) {
  return findElement(map, e => e.role === 'textbox' || e.category === 'input' || e.contentEditable === 'true')
}

export function findSearchInput(map) {
  return findElement(map, e => 
    e.ariaLabel?.includes('Search') || 
    e.placeholder?.includes('Search') ||
    e.testId === 'search-input' ||
    e.testId === 'search'
  )
}

export function findMessageInput(map) {
  return findElement(map, e => 
    e.ariaLabel === 'Type a message' || 
    e.role === 'textbox' ||
    e.testId === 'message-input' ||
    e.testId === 'composer'
  )
}

export function findNavTriggers(map) {
  const results = []
  for (const [screenName, screen] of Object.entries(map.screens || {})) {
    for (const el of screen.elements || []) {
      if (el.isNavTrigger) {
        results.push({ ...el, screen: screenName })
      }
    }
  }
  return results
}