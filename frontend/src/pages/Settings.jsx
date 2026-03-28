import { useState, useEffect } from 'react'
import { getSettings, updateSettings } from '../api/settings'
import GlassCard from '../components/GlassCard'
import Button from '../components/Button'
import ErrorMessage from '../components/ErrorMessage'
import styles from './Settings.module.css'

export default function Settings() {
  const [mockMode, setMockMode] = useState(true)
  const [device, setDevice] = useState('cpu')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    loadSettings()
  }, [])

  const loadSettings = async () => {
    try {
      setLoading(true)
      const data = await getSettings()
      setMockMode(data.ml_mock_mode === 'true')
      setDevice(data.ml_device || 'cpu')
    } catch (err) {
      setError('Failed to load settings')
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    try {
      setSaving(true)
      setError('')
      setSaved(false)
      await updateSettings({
        ml_mock_mode: String(mockMode),
        ml_device: device,
      })
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } catch (err) {
      setError('Failed to save settings')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="pageEnter">
        <h1 className={styles.title}>Settings</h1>
        <GlassCard>
          <p className={styles.loadingText}>Loading settings...</p>
        </GlassCard>
      </div>
    )
  }

  return (
    <div className="pageEnter">
      <h1 className={styles.title}>Settings</h1>
      <p className={styles.subtitle}>Configure the ML inference pipeline</p>

      <GlassCard>
        <ErrorMessage message={error} />

        <div className={styles.section}>
          <div className={styles.sectionHeader}>
            <h2 className={styles.sectionTitle}>Inference Mode</h2>
            <p className={styles.sectionDesc}>
              Toggle between mock (test cube) and real TripoSR model inference.
            </p>
          </div>

          <div className={styles.toggleRow}>
            <span className={styles.toggleLabel}>
              {mockMode ? 'Mock Mode' : 'TripoSR (Real)'}
            </span>
            <button
              type="button"
              className={`${styles.toggle} ${!mockMode ? styles.toggleActive : ''}`}
              onClick={() => setMockMode(!mockMode)}
              aria-label="Toggle mock mode"
            >
              <span className={styles.toggleThumb} />
            </button>
          </div>

          <div className={styles.badge}>
            {mockMode ? (
              <span className={styles.badgeMock}>MOCK</span>
            ) : (
              <span className={styles.badgeReal}>REAL</span>
            )}
          </div>
        </div>

        <div className={styles.divider} />

        <div className={styles.section}>
          <div className={styles.sectionHeader}>
            <h2 className={styles.sectionTitle}>Device</h2>
            <p className={styles.sectionDesc}>
              Select compute device for inference. GPU requires NVIDIA with CUDA support.
            </p>
          </div>

          <div className={styles.devicePicker}>
            {['cpu', 'cuda:0'].map((d) => (
              <button
                key={d}
                type="button"
                className={`${styles.deviceOption} ${device === d ? styles.deviceActive : ''}`}
                onClick={() => setDevice(d)}
              >
                <span className={styles.deviceIcon}>
                  {d === 'cpu' ? '🖥' : '⚡'}
                </span>
                <span className={styles.deviceName}>
                  {d === 'cpu' ? 'CPU' : 'GPU (CUDA)'}
                </span>
              </button>
            ))}
          </div>
        </div>

        <div className={styles.divider} />

        <div className={styles.actions}>
          <Button
            onClick={handleSave}
            disabled={saving}
            loading={saving}
          >
            {saving ? 'Saving...' : 'Save Settings'}
          </Button>
          {saved && (
            <span className={styles.savedMessage}>Settings saved! Changes apply on next task.</span>
          )}
        </div>
      </GlassCard>
    </div>
  )
}
