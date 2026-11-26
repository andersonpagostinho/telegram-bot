import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../services/api';
import { useAuthStore } from '../store/auth';

export default function Login() {
  const navigate = useNavigate();
  const setAuth = useAuthStore((state) => state.setAuth);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    console.log('=== LOGIN STARTED ===');
    setError(null);

    if (!email || !password) {
      console.log('Validation failed');
      setError('Email e senha são obrigatórios');
      return;
    }

    setIsLoading(true);
    console.log('Making API call...');

    try {
      console.log('API call in progress...');
      const response = await apiClient.login({ email, password });
      console.log('Response received:', response);

      if (response?.access_token) {
        console.log('Token found, setting up...');
        apiClient.setToken(response.access_token);

        // Extract user info from JWT payload
        try {
          const parts = response.access_token.split('.');
          if (parts.length >= 2) {
            const payload = JSON.parse(atob(parts[1]));
            const userData = {
              user_id: payload.user_id || 'unknown',
              tenant_id: payload.tenant_id || 'unknown',
              actor_id: payload.actor_id || payload.user_id || 'unknown',
              actor_role: payload.actor_role || 'admin',
            };

            localStorage.setItem('auth_token', response.access_token);
            localStorage.setItem('auth_user', JSON.stringify(userData));
            setAuth(userData, response.access_token);
          } else {
            throw new Error('Invalid token format');
          }
        } catch (err) {
          console.error('Failed to parse JWT:', err);
          setError('Erro ao processar token de autenticação');
          return;
        }

        console.log('Navigating to home...');
        navigate('/');
      } else {
        console.log('No token in response');
        setError('Sem token na resposta');
      }
    } catch (err: any) {
      console.error('Full error:', err);
      console.error('Error code:', err?.code);
      console.error('Error message:', err?.message);
      console.error('Error response:', err?.response);
      console.error('Error response status:', err?.response?.status);
      console.error('Error response data:', err?.response?.data);
      console.error('Error stack:', err?.stack);
      setError(err?.response?.data?.detail || err?.message || 'Erro ao fazer login');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={{ padding: '20px', maxWidth: '400px', margin: '100px auto', fontFamily: 'sans-serif' }}>
      <h1>NeoEve Command Center</h1>
      <p>Faça login para continuar</p>

      {error && (
        <div style={{ backgroundColor: '#fee', color: '#c00', padding: '10px', marginBottom: '10px', borderRadius: '4px' }}>
          {error}
        </div>
      )}

      <form onSubmit={handleLogin}>
        <div style={{ marginBottom: '15px' }}>
          <label style={{ display: 'block', marginBottom: '5px' }}>Email:</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            disabled={isLoading}
            style={{
              width: '100%',
              padding: '8px',
              fontSize: '14px',
              boxSizing: 'border-box',
              border: '1px solid #ccc',
              borderRadius: '4px',
            }}
            placeholder="seu@email.com"
          />
        </div>

        <div style={{ marginBottom: '15px' }}>
          <label style={{ display: 'block', marginBottom: '5px' }}>Senha:</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={isLoading}
            style={{
              width: '100%',
              padding: '8px',
              fontSize: '14px',
              boxSizing: 'border-box',
              border: '1px solid #ccc',
              borderRadius: '4px',
            }}
            placeholder="••••••••"
          />
        </div>

        <button
          type="submit"
          disabled={isLoading}
          style={{
            width: '100%',
            padding: '10px',
            fontSize: '16px',
            backgroundColor: '#0066cc',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: isLoading ? 'not-allowed' : 'pointer',
            opacity: isLoading ? 0.6 : 1,
          }}
        >
          {isLoading ? 'Entrando...' : 'Entrar'}
        </button>
      </form>
    </div>
  );
}
