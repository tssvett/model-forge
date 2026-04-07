import { Link, Outlet } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import AnimatedBackground from './AnimatedBackground'
import Button from './Button'
import styles from './Layout.module.css'

export default function Layout() {
  const { user, logout } = useAuth()

  return (
    <div className={styles.wrapper}>
      <AnimatedBackground />
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
            <Link to="/analytics" className={styles.navLink}>
              Analytics
            </Link>
            <Link to="/settings" className={styles.navLink}>
              Settings
            </Link>
          </nav>
          <div className={styles.userSection}>
            <span className={styles.email}>{user?.email}</span>
            <Button variant="secondary" onClick={logout} style={{ padding: '6px 16px', fontSize: '13px' }}>
              Logout
            </Button>
          </div>
        </div>
      </header>
      <main className={styles.main}>
        <Outlet />
      </main>
    </div>
  )
}
