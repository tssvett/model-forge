import Button from './Button'
import styles from './Pagination.module.css'

export default function Pagination({ page, totalPages, onPageChange }) {
  if (totalPages <= 1) return null

  return (
    <div className={styles.pagination}>
      <Button
        variant="secondary"
        onClick={() => onPageChange(page - 1)}
        disabled={page === 0}
        style={{ padding: '8px 16px', fontSize: '13px' }}
      >
        Previous
      </Button>
      <span className={styles.info}>
        Page {page + 1} of {totalPages}
      </span>
      <Button
        variant="secondary"
        onClick={() => onPageChange(page + 1)}
        disabled={page >= totalPages - 1}
        style={{ padding: '8px 16px', fontSize: '13px' }}
      >
        Next
      </Button>
    </div>
  )
}
