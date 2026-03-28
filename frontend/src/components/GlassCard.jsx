import styles from './GlassCard.module.css'

export default function GlassCard({ children, className = '', glow = false }) {
  const classes = [
    styles.card,
    glow ? styles.glow : '',
    className,
  ].filter(Boolean).join(' ')

  return <div className={classes}>{children}</div>
}
