import styles from './LoadingSpinner.module.css'

const SIZES = {
  sm: 24,
  md: 40,
  lg: 56,
}

export default function LoadingSpinner({ text = 'Loading...', size = 'md' }) {
  const dimension = SIZES[size] || SIZES.md

  return (
    <div className={styles.container}>
      <div
        className={styles.spinner}
        style={{ width: dimension, height: dimension }}
      />
      {text && <p className={styles.text}>{text}</p>}
    </div>
  )
}
