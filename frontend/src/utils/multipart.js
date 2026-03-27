export function parseMultipartResponse(arrayBuffer, contentType) {
  const boundaryMatch = contentType.match(/boundary=(.+)/)
  if (!boundaryMatch) {
    throw new Error('No boundary found in Content-Type')
  }
  const boundary = boundaryMatch[1]

  const uint8 = new Uint8Array(arrayBuffer)
  const text = new TextDecoder().decode(uint8)

  const parts = text.split(`--${boundary}`).filter((part) => {
    const trimmed = part.trim()
    return trimmed && trimmed !== '--'
  })

  let metadata = null
  let fileBlob = null
  let filename = 'model.glb'

  for (const part of parts) {
    const headerEnd = part.indexOf('\r\n\r\n')
    if (headerEnd === -1) continue

    const headers = part.substring(0, headerEnd)
    const bodyText = part.substring(headerEnd + 4)

    const filenameMatch = headers.match(/filename="([^"]+)"/)
    if (filenameMatch) {
      filename = filenameMatch[1]

      // For binary data, find the part boundaries in the original buffer
      const partBoundary = `--${boundary}`
      const textBefore = text.indexOf(headers)
      const bodyStart = textBefore + headers.length + 4 // +4 for \r\n\r\n
      const nextBoundary = text.indexOf(partBoundary, bodyStart)
      const bodyEnd = nextBoundary > 0 ? nextBoundary - 2 : uint8.length // -2 for \r\n

      const encoder = new TextEncoder()
      const byteOffset = encoder.encode(text.substring(0, bodyStart)).length
      const byteEnd = encoder.encode(text.substring(0, bodyEnd)).length

      fileBlob = new Blob([uint8.slice(byteOffset, byteEnd)], {
        type: 'application/octet-stream',
      })
    } else if (headers.includes('application/json')) {
      const jsonStr = bodyText.replace(/\r\n$/, '').trim()
      metadata = JSON.parse(jsonStr)
    }
  }

  return { metadata, fileBlob, filename }
}
