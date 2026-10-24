import { connectAiControl } from './ai-control-client.mjs'

async function inspect() {
  const client = await connectAiControl()
  try {
    const info = await client.evaluate(`(() => {
      // Find webviews, iframes, browser controls
      const webviews = Array.from(document.querySelectorAll('webview')).map(w => ({
        src: w.getAttribute('src'),
        id: w.id,
        className: w.className
      }));
      const iframes = Array.from(document.querySelectorAll('iframe')).map(f => ({
        src: f.getAttribute('src'),
        id: f.id
      }));

      // Look for browser tab elements or Workstation browser indicators
      const browserTabs = Array.from(document.querySelectorAll('[data-testid*="browser"], [data-testid*="tab"], [role="tab"]')).map(t => ({
        text: t.textContent?.trim(),
        role: t.getAttribute('role'),
        testId: t.getAttribute('data-testid')
      }));

      return {
        title: document.title,
        url: location.href,
        webviews,
        iframes,
        browserTabs: browserTabs.slice(0, 15)
      };
    })()`)
    console.log(JSON.stringify(info, null, 2))
  } finally {
    client.close()
  }
}

inspect().catch(err => {
  console.error(err)
  process.exit(1)
})
