import styles from './Button.module.css'

export default function Button({
  children,
  variant = 'primary',
  loading = false,
  disabled = false,
  className = '',
  ...rest
}) {
  const classes = [
    styles.button,
    styles[variant],
    className,
  ].filter(Boolean).join(' ')

  return (
    <button
      className={classes}
      disabled={disabled || loading}
      {...rest}
    >
      {loading && <span className={styles.spinnerInline} />}
      {children}
    </button>
  )
}
