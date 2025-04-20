import './App.css'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Home from './pages/Home'
import ServicePage from './pages/ServicePage'
import { AlertProvider } from './context/AlertContext' // 👈 import the provider

function App() {
  return (
    <AlertProvider>
      <Router>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/service/:name" element={<ServicePage />} />
        </Routes>
      </Router>
    </AlertProvider>
  )
}

export default App
