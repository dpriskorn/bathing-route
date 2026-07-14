const COMMONS_API = 'https://commons.wikimedia.org/w/api.php'
const USER_AGENT = 'bathing-route/0.1 (Python; https://github.com/anomalyco/bathing-route)'

export interface CommonsImageInfo {
  url: string
  thumburl: string
}

export async function batchFetchImageUrls(filenames: string[]): Promise<Record<string, CommonsImageInfo>> {
  const results: Record<string, CommonsImageInfo> = {}
  const batchSize = 50

  for (let i = 0; i < filenames.length; i += batchSize) {
    const batch = filenames.slice(i, i + batchSize)
    const titles = batch.map(f => `File:${f}`).join('|')
    const url = `${COMMONS_API}?action=query&titles=${encodeURIComponent(titles)}&prop=imageinfo&iiprop=url|thumburl&iiurlwidth=400&format=json`

    const resp = await fetch(url, {
      headers: { 'User-Agent': USER_AGENT },
    })
    const data = await resp.json()
    const pages = data.query?.pages || {}

    for (const page of Object.values(pages) as Record<string, any>[]) {
      const info = page.imageinfo?.[0]
      if (info) {
        const filename = page.title.replace(/^File:/, '')
        results[filename] = { url: info.url, thumburl: info.thumburl }
      }
    }
  }
  return results
}
