import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { createTask } from '../api/tasks'
import { validateFile, ALLOWED_EXTENSIONS } from '../utils/validation'
import styles from './TaskCreate.module.css'

export default function TaskCreate() {
  const navigate = useNavigate()
  const fileInputRef = useRef(null)
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [prompt, setPrompt] = useState('')
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
      const task = await createTask(file, prompt || null, setProgress)
      navigate(`/tasks/${task.id}`)
    } catch (err) {
      setError(err.response?.data?.message || 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  const formatSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  return (
    <div>
      <h1 className={styles.title}>Create New Task</h1>

      {error && <div className={styles.error}>{error}</div>}

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
              <p className={styles.dropzoneText}>
                Drag and drop an image here, or click to select
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
                <p className={styles.fileSize}>{formatSize(file.size)}</p>
                <button
                  type="button"
                  className={styles.removeBtn}
                  onClick={(e) => { e.stopPropagation(); clearFile() }}
                >
                  Remove
                </button>
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

        <div className={styles.field}>
          <label htmlFor="prompt" className={styles.label}>
            Prompt (optional)
          </label>
          <input
            id="prompt"
            type="text"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            className={styles.input}
            placeholder="Describe the 3D model you want..."
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

        <button
          type="submit"
          className={styles.submitBtn}
          disabled={!file || uploading}
        >
          {uploading ? 'Uploading...' : 'Create Task'}
        </button>
      </form>
    </div>
  )
}
