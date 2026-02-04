import { useState, useEffect } from 'react'
import axios from 'axios'
import reactLogo from './assets/react.svg'
import viteLogo from '/vite.svg'
import './App.css'

interface ApiResponse {
  message?: string;
  status?: string;
  [key: string]: any;
}

function App() {
  const [data, setData] = useState<ApiResponse | null>(null)
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        // Try the root endpoint first
        const response = await axios.get('http://127.0.0.1:8000/');
        setData(response.data);
        setError(null);
      } catch (err) {
        console.error("Failed to fetch from root, trying /api/health", err);
        try {
            // Fallback to /api/health if root fails (or if the user intended that)
            const response = await axios.get('http://127.0.0.1:8000/api/health');
            setData(response.data);
            setError(null);
        } catch (retryErr) {
            setError('Failed to connect to backend API');
            console.error(retryErr);
        }
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [])

  return (
    <>
      <div>
        <a href="https://vite.dev" target="_blank">
          <img src={viteLogo} className="logo" alt="Vite logo" />
        </a>
        <a href="https://react.dev" target="_blank">
          <img src={reactLogo} className="logo react" alt="React logo" />
        </a>
      </div>
      <h1>Daily Stock Analysis</h1>
      
      <div className="card">
        <h2>Backend Connection Status</h2>
        
        {loading && <p>Connecting to backend...</p>}
        
        {error && (
          <div style={{ color: 'red', border: '1px solid red', padding: '10px', borderRadius: '4px' }}>
            <p><strong>Error:</strong> {error}</p>
            <p style={{ fontSize: '0.8em' }}>Make sure the backend server is running on port 8000</p>
          </div>
        )}

        {data && (
          <div style={{ color: '#4caf50', border: '1px solid #4caf50', padding: '10px', borderRadius: '4px' }}>
             <p><strong>API Status:</strong> Connected ✅</p>
             <pre style={{ textAlign: 'left', background: '#f5f5f5', padding: '10px', borderRadius: '4px', overflow: 'auto', color: '#333' }}>
               {JSON.stringify(data, null, 2)}
             </pre>
          </div>
        )}
      </div>
      
      <p className="read-the-docs">
        Check the console for more details
      </p>
    </>
  )
}

export default App
