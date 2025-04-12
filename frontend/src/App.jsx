import './App.css'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Home from './pages/Home'
import ServicePage from './pages/ServicePage'

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/service/:name" element={<ServicePage />} />
      </Routes>
    </Router>
  )
}

export default App
