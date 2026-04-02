import { Navigate } from 'react-router-dom'
import useAuth from '../hooks/useAuth'

/**
 * Client-side guard for admin-only routes.
 * The backend enforces the same check via get_admin_user dependency (HTTP 403).
 * This layer prevents rendering the page for non-admins before they even hit the API.
 */
export default function AdminRoute({ children }) {
  const { token, user } = useAuth()

  if (!token) return <Navigate to="/login" replace />
  if (!user?.is_admin) return <Navigate to="/dashboard" replace />

  return children
}
