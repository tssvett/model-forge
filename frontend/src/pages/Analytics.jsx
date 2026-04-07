import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { getAnalyticsSummary, getAnalyticsTimeline, getTasksWithMetrics } from '../api/tasks'
import { formatRelativeDate } from '../utils/format'
import StatusBadge from '../components/StatusBadge'
import GlassCard from '../components/GlassCard'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorMessage from '../components/ErrorMessage'
import Pagination from '../components/Pagination'
import styles from './Analytics.module.css'

export default function Analytics() {
  const [summary, setSummary] = useState(null)
  const [timeline, setTimeline] = useState(null)
  const [tasksWithMetrics, setTasksWithMetrics] = useState(null)
  const [page, setPage] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [timelineDays, setTimelineDays] = useState(30)

  useEffect(() => {
    async function fetchData() {
      setLoading(true)
      setError(null)
      try {
        const [summaryData, timelineData, metricsData] = await Promise.all([
          getAnalyticsSummary(),
          getAnalyticsTimeline(timelineDays),
          getTasksWithMetrics(page, 10),
        ])
        setSummary(summaryData)
        setTimeline(timelineData)
        setTasksWithMetrics(metricsData)
      } catch (err) {
        setError(err.response?.data?.message || 'Failed to load analytics')
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [page, timelineDays])

  const formatMetric = (value, decimals = 4) => {
    if (value == null) return '-'
    return Number(value).toFixed(decimals)
  }

  const formatPercent = (value) => {
    if (value == null) return '-'
    return `${Number(value).toFixed(1)}%`
  }

  if (loading) return <LoadingSpinner text="Loading analytics..." />

  return (
    <div className="pageEnter">
      <div className={styles.header}>
        <div>
          <h1 className={styles.title}>Analytics</h1>
          <p className={styles.subtitle}>Task generation statistics and quality metrics</p>
        </div>
      </div>

      <ErrorMessage message={error} />

      {summary && (
        <div className={styles.summaryGrid}>
          <GlassCard className={styles.statCard}>
            <div className={styles.statLabel}>Total Tasks</div>
            <div className={styles.statValue}>{summary.totalTasks}</div>
          </GlassCard>
          <GlassCard className={styles.statCard}>
            <div className={styles.statLabel}>Success Rate</div>
            <div className={`${styles.statValue} ${styles.successRate}`}>
              {formatPercent(summary.successRate)}
            </div>
          </GlassCard>
          <GlassCard className={styles.statCard}>
            <div className={styles.statLabel}>Completed</div>
            <div className={`${styles.statValue} ${styles.completed}`}>{summary.completedTasks}</div>
          </GlassCard>
          <GlassCard className={styles.statCard}>
            <div className={styles.statLabel}>Failed</div>
            <div className={`${styles.statValue} ${styles.failed}`}>{summary.failedTasks}</div>
          </GlassCard>
          <GlassCard className={styles.statCard}>
            <div className={styles.statLabel}>Avg Inference</div>
            <div className={styles.statValue}>
              {summary.avgInferenceTimeSec != null ? `${Number(summary.avgInferenceTimeSec).toFixed(2)}s` : '-'}
            </div>
          </GlassCard>
          <GlassCard className={styles.statCard}>
            <div className={styles.statLabel}>Pending</div>
            <div className={styles.statValue}>{summary.pendingTasks}</div>
          </GlassCard>
        </div>
      )}

      {summary && (
        <GlassCard className={styles.metricsSection}>
          <h2 className={styles.sectionTitle}>Average Quality Metrics</h2>
          <div className={styles.metricsGrid}>
            <div className={styles.metricItem}>
              <span className={styles.metricLabel}>Chamfer Distance</span>
              <span className={styles.metricValue}>{formatMetric(summary.avgChamferDistance)}</span>
            </div>
            <div className={styles.metricItem}>
              <span className={styles.metricLabel}>IoU 3D</span>
              <span className={styles.metricValue}>{formatMetric(summary.avgIou3d)}</span>
            </div>
            <div className={styles.metricItem}>
              <span className={styles.metricLabel}>F-Score</span>
              <span className={styles.metricValue}>{formatMetric(summary.avgFScore)}</span>
            </div>
            <div className={styles.metricItem}>
              <span className={styles.metricLabel}>Normal Consistency</span>
              <span className={styles.metricValue}>{formatMetric(summary.avgNormalConsistency)}</span>
            </div>
            <div className={styles.metricItem}>
              <span className={styles.metricLabel}>Avg Vertices</span>
              <span className={styles.metricValue}>{formatMetric(summary.avgVertices, 0)}</span>
            </div>
            <div className={styles.metricItem}>
              <span className={styles.metricLabel}>Avg Faces</span>
              <span className={styles.metricValue}>{formatMetric(summary.avgFaces, 0)}</span>
            </div>
          </div>
        </GlassCard>
      )}

      {timeline && timeline.entries.length > 0 && (
        <GlassCard className={styles.timelineSection}>
          <div className={styles.timelineHeader}>
            <h2 className={styles.sectionTitle}>Task Timeline</h2>
            <div className={styles.timelineFilters}>
              {[7, 14, 30, 90].map((d) => (
                <button
                  key={d}
                  className={`${styles.timelineBtn} ${timelineDays === d ? styles.timelineBtnActive : ''}`}
                  onClick={() => setTimelineDays(d)}
                >
                  {d}d
                </button>
              ))}
            </div>
          </div>
          <div className={styles.timelineChart}>
            {timeline.entries.map((entry) => {
              const maxTotal = Math.max(...timeline.entries.map(e => e.total), 1)
              const height = Math.max((entry.total / maxTotal) * 100, 4)
              return (
                <div key={entry.date} className={styles.timelineBar} title={`${entry.date}: ${entry.total} tasks`}>
                  <div className={styles.barContainer}>
                    <div
                      className={styles.barFill}
                      style={{ height: `${height}%` }}
                    >
                      <div
                        className={styles.barCompleted}
                        style={{ height: entry.total > 0 ? `${(entry.completed / entry.total) * 100}%` : '0%' }}
                      />
                    </div>
                  </div>
                  <span className={styles.barLabel}>{entry.date.slice(5)}</span>
                </div>
              )
            })}
          </div>
          <div className={styles.timelineLegend}>
            <span className={styles.legendItem}>
              <span className={styles.legendDot} style={{ background: 'var(--color-accent)' }} /> Completed
            </span>
            <span className={styles.legendItem}>
              <span className={styles.legendDot} style={{ background: 'rgba(255,255,255,0.15)' }} /> Other
            </span>
          </div>
        </GlassCard>
      )}

      {tasksWithMetrics && (
        <GlassCard className={styles.tableCard}>
          <h2 className={styles.sectionTitle}>Tasks with Metrics</h2>
          <div className={styles.tableWrapper}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Status</th>
                  <th>Created</th>
                  <th>Chamfer</th>
                  <th>IoU</th>
                  <th>F-Score</th>
                  <th>Inference</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {tasksWithMetrics.content.map(({ task, metrics }) => (
                  <tr key={task.id} className={styles.row}>
                    <td className={styles.idCell}>{task.id.substring(0, 8)}</td>
                    <td><StatusBadge status={task.status} /></td>
                    <td className={styles.dateCell}>{formatRelativeDate(task.createdAt)}</td>
                    <td className={styles.metricCell}>{formatMetric(metrics?.chamferDistance)}</td>
                    <td className={styles.metricCell}>{formatMetric(metrics?.iou3d)}</td>
                    <td className={styles.metricCell}>{formatMetric(metrics?.fScore)}</td>
                    <td className={styles.metricCell}>
                      {metrics?.inferenceTimeSec != null ? `${Number(metrics.inferenceTimeSec).toFixed(2)}s` : '-'}
                    </td>
                    <td>
                      <Link to={`/tasks/${task.id}`} className={styles.viewLink}>
                        View
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <polyline points="9 18 15 12 9 6" />
                        </svg>
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pagination page={page} totalPages={tasksWithMetrics.totalPages} onPageChange={setPage} />
        </GlassCard>
      )}
    </div>
  )
}
