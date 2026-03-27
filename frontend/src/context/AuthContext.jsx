import { createContext, useContext, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import * as authApi from '../api/auth'

const AuthContext = createContext(null)

function decodeToken(token) {
  try {
    const payload = token.split('.')[1]
    const decoded = JSON.parse(atob(payload))
    return { email: decoded.sub || decoded.email }
  } catch {
    return null
  }
}

export function AuthProvider({ children }) {
  const navigate = useNavigate()
  const [token, setToken] = useState(() => localStorage.getItem('token'))
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('token')
    return saved ? decodeToken(saved) : null
  })

  const login = useCallback(async (email, password) => {
    const data = await authApi.login(email, password)
    localStorage.setItem('token', data.accessToken)
    setToken(data.accessToken)
    setUser(decodeToken(data.accessToken))
    navigate('/dashboard')
  }, [navigate])

  const registerUser = useCallback(async (email, password) => {
    const data = await authApi.register(email, password)
    localStorage.setItem('token', data.accessToken)
    setToken(data.accessToken)
    setUser(decodeToken(data.accessToken))
    navigate('/dashboard')
  }, [navigate])

  const logout = useCallback(() => {
    localStorage.removeItem('token')
    setToken(null)
    setUser(null)
    navigate('/login')
  }, [navigate])

  const value = {
    token,
    user,
    isAuthenticated: !!token,
    login,
    register: registerUser,
    logout,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
