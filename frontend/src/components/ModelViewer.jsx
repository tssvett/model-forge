import { useEffect } from 'react'
import styles from './ModelViewer.module.css'

export default function ModelViewer({ src, alt = '3D Model' }) {
  useEffect(() => {
    import('@google/model-viewer')
  }, [])

  if (!src) return null

  return (
    <div className={styles.container}>
      <model-viewer
        src={src}
        alt={alt}
        auto-rotate
        camera-controls
        shadow-intensity="0.5"
        environment-image="neutral"
        exposure="1"
        style={{ width: '100%', height: '100%', '--poster-color': 'transparent' }}
      />
      <div className={styles.label}>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
          <circle cx="12" cy="12" r="3" />
        </svg>
        Drag to rotate &middot; Scroll to zoom
      </div>
    </div>
  )
}
