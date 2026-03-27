import styles from './Pagination.module.css'

export default function Pagination({ page, totalPages, onPageChange }) {
  if (totalPages <= 1) return null

  return (
    <div className={styles.pagination}>
      <button
        className={styles.btn}
        onClick={() => onPageChange(page - 1)}
        disabled={page === 0}
      >
        Previous
      </button>
      <span className={styles.info}>
        Page {page + 1} of {totalPages}
      </span>
      <button
        className={styles.btn}
        onClick={() => onPageChange(page + 1)}
        disabled={page >= totalPages - 1}
      >
        Next
      </button>
    </div>
  )
}
