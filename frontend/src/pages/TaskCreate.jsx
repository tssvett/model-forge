import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { createTask } from '../api/tasks'
import { validateFile, ALLOWED_EXTENSIONS } from '../utils/validation'
import { formatFileSize } from '../utils/format'
import GlassCard from '../components/GlassCard'
import Button from '../components/Button'
import ErrorMessage from '../components/ErrorMessage'
import styles from './TaskCreate.module.css'

export default function TaskCreate() {
  const navigate = useNavigate()
  const fileInputRef = useRef(null)
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [progress, setProgress] = useState(0)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  const [dragOver, setDragOver] = useState(false)

  const handleFile = (selectedFile) => {
    setError('')
    const result = validateFile(selectedFile)
    if (!result.valid) {
      setError(result.error)
      return
    }
    setFile(selectedFile)
    setPreview(URL.createObjectURL(selectedFile))
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    const droppedFile = e.dataTransfer.files[0]
    if (droppedFile) handleFile(droppedFile)
  }

  const handleDragOver = (e) => {
    e.preventDefault()
    setDragOver(true)
  }

  const handleDragLeave = () => setDragOver(false)

  const handleInputChange = (e) => {
    const selected = e.target.files[0]
    if (selected) handleFile(selected)
  }

  const clearFile = () => {
    setFile(null)
    if (preview) URL.revokeObjectURL(preview)
    setPreview(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!file) return
    setError('')
    setUploading(true)
    setProgress(0)
    try {
      const task = await createTask(file, setProgress)
      navigate(`/tasks/${task.id}`)
    } catch (err) {
      setError(err.response?.data?.message || 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="pageEnter">
      <h1 className={styles.title}>Create New Task</h1>
      <p className={styles.subtitle}>Upload an image to generate a 3D model</p>

      <GlassCard>
        <ErrorMessage message={error} />

        <form onSubmit={handleSubmit}>
          <div
            className={`${styles.dropzone} ${dragOver ? styles.dragOver : ''} ${file ? styles.hasFile : ''}`}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onClick={() => !file && fileInputRef.current?.click()}
          >
            {!file ? (
              <div className={styles.dropzoneContent}>
                <div className={styles.uploadIcon}>
                  <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
                    <polyline points="17 8 12 3 7 8" />
                    <line x1="12" y1="3" x2="12" y2="15" />
                  </svg>
                </div>
                <p className={styles.dropzoneText}>
                  Drag and drop an image here, or click to browse
                </p>
                <p className={styles.dropzoneHint}>
                  Supported: {ALLOWED_EXTENSIONS} (max 10 MB)
                </p>
              </div>
            ) : (
              <div className={styles.previewContainer}>
                <img src={preview} alt="Preview" className={styles.previewImage} />
                <div className={styles.fileInfo}>
                  <p className={styles.fileName}>{file.name}</p>
                  <p className={styles.fileSize}>{formatFileSize(file.size)}</p>
                  <Button
                    type="button"
                    variant="danger"
                    onClick={(e) => { e.stopPropagation(); clearFile() }}
                    style={{ marginTop: '10px', padding: '6px 14px', fontSize: '12px' }}
                  >
                    Remove
                  </Button>
                </div>
              </div>
            )}
            <input
              ref={fileInputRef}
              type="file"
              accept={ALLOWED_EXTENSIONS}
              onChange={handleInputChange}
              className={styles.hiddenInput}
            />
          </div>

          {uploading && (
            <div className={styles.progressWrapper}>
              <div className={styles.progressBar}>
                <div
                  className={styles.progressFill}
                  style={{ width: `${progress}%` }}
                />
              </div>
              <span className={styles.progressText}>{progress}%</span>
            </div>
          )}

          <Button
            type="submit"
            disabled={!file || uploading}
            loading={uploading}
            style={{ width: '100%' }}
          >
            {uploading ? 'Uploading...' : 'Generate 3D Model'}
          </Button>
        </form>
      </GlassCard>
    </div>
  )
}
