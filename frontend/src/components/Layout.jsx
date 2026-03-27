import { Link, Outlet } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import styles from './Layout.module.css'

export default function Layout() {
  const { user, logout } = useAuth()

  return (
    <div className={styles.wrapper}>
      <header className={styles.header}>
        <div className={styles.headerInner}>
          <Link to="/dashboard" className={styles.logo}>
            ModelForge
          </Link>
          <nav className={styles.nav}>
            <Link to="/dashboard" className={styles.navLink}>
              Dashboard
            </Link>
            <Link to="/tasks/new" className={styles.navLink}>
              New Task
            </Link>
          </nav>
          <div className={styles.userSection}>
            <span className={styles.email}>{user?.email}</span>
            <button onClick={logout} className={styles.logoutBtn}>
              Logout
            </button>
          </div>
        </div>
      </header>
      <main className={styles.main}>
        <Outlet />
      </main>
    </div>
  )
}
