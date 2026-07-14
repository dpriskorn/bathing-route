import type { BathingSpotFeature, SpotDetails } from '../composables/useRoute'

export function spotsToGpx(
  spots: BathingSpotFeature[],
  spotDetails: Record<string, SpotDetails>,
  layerName: string
): string {
  const lines: string[] = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<gpx version="1.1" creator="bathing-route" xmlns="http://www.topografix.com/GPX/1/1">',
  ]

  for (const spot of spots) {
    const details = spotDetails[spot.properties.qid]
    const name = details?.label || spot.properties.qid
    const wikidataUrl = details?.wikidata_url || `https://www.wikidata.org/wiki/${spot.properties.qid}`
    const desc = `${spot.properties.qid} - ${wikidataUrl}`
    const link = details?.image_url ? `<link href="${escapeXml(details.image_url)}"/>` : ''

    lines.push(`  <wpt lat="${spot.geometry.coordinates[1]}" lon="${spot.geometry.coordinates[0]}">`)
    lines.push(`    <name>${escapeXml(name)}</name>`)
    lines.push(`    <desc>${escapeXml(desc)}</desc>`)
    lines.push(`    <type>${escapeXml(layerName)}</type>`)
    if (link) lines.push(`    ${link}`)
    lines.push('  </wpt>')
  }

  lines.push('</gpx>')
  return lines.join('\n')
}

function escapeXml(str: string): string {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;')
}

export function downloadGpx(
  spots: BathingSpotFeature[],
  spotDetails: Record<string, SpotDetails>,
  layerId: string,
  layerName: string
): void {
  const gpx = spotsToGpx(spots, spotDetails, layerName)
  const blob = new Blob([gpx], { type: 'application/gpx+xml' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `bathing-spots-${layerId}.gpx`
  a.click()
  URL.revokeObjectURL(url)
}
