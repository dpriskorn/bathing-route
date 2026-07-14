const API_BASE = '/api'

export interface CommonsImageInfo {
  url: string
  thumburl: string
}

export async function batchFetchImageUrls(filenames: string[]): Promise<Record<string, CommonsImageInfo>> {
  const results: Record<string, CommonsImageInfo> = {}

  for (const filename of filenames) {
    try {
      let cleanFilename = filename
      if (filename.startsWith('Special:FilePath/')) {
        cleanFilename = filename.slice('Special:FilePath/'.length)
      }

      const resp = await fetch(`${API_BASE}/commons-image?filename=${encodeURIComponent(cleanFilename)}`)
      if (resp.ok) {
        const data = await resp.json()
        if (data.url) {
          results[cleanFilename] = { url: data.url, thumburl: data.thumburl || data.url }
        }
      }
    } catch {
      // skip failures
    }
  }
  return results
}
