import { useState, useEffect, useCallback, useRef } from 'react'
import { downloadTask } from '../api/tasks'
import { parseMultipartResponse } from '../utils/multipart'

export function useModelDownload(taskId, enabled = false) {
  const [modelBlobUrl, setModelBlobUrl] = useState(null)
  const [filename, setFilename] = useState('model.glb')
  const [downloading, setDownloading] = useState(false)
  const [error, setError] = useState(null)
  const blobUrlRef = useRef(null)

  useEffect(() => {
    if (!enabled || !taskId) return
    let cancelled = false

    const fetchModel = async () => {
      setDownloading(true)
      setError(null)
      try {
        const { data, contentType } = await downloadTask(taskId)
        const { fileBlob, filename: fname } = parseMultipartResponse(data, contentType)
        if (cancelled) return
        if (!fileBlob) {
          setError('Failed to parse model data')
          return
        }
        setFilename(fname)
        const url = URL.createObjectURL(fileBlob)
        blobUrlRef.current = url
        setModelBlobUrl(url)
      } catch (err) {
        if (!cancelled) {
          setError(err.response?.data?.message || err.message || 'Download failed')
        }
      } finally {
        if (!cancelled) setDownloading(false)
      }
    }

    fetchModel()

    return () => {
      cancelled = true
    }
  }, [taskId, enabled])

  useEffect(() => {
    return () => {
      if (blobUrlRef.current) {
        URL.revokeObjectURL(blobUrlRef.current)
      }
    }
  }, [])

  const triggerFileDownload = useCallback(async () => {
    let url = modelBlobUrl

    if (!url) {
      setDownloading(true)
      try {
        const { data, contentType } = await downloadTask(taskId)
        const { fileBlob, filename: fname } = parseMultipartResponse(data, contentType)
        if (!fileBlob) {
          setError('Failed to parse model data')
          return
        }
        url = URL.createObjectURL(fileBlob)
        setFilename(fname)
      } catch (err) {
        setError(err.response?.data?.message || err.message || 'Download failed')
        return
      } finally {
        setDownloading(false)
      }
    }

    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)

    if (url !== modelBlobUrl) {
      URL.revokeObjectURL(url)
    }
  }, [taskId, modelBlobUrl, filename])

  const isViewerCompatible = /\.(glb|gltf)$/i.test(filename)

  return { modelBlobUrl, filename, downloading, error, triggerFileDownload, isViewerCompatible }
}
