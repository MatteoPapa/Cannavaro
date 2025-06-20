import React from 'react'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import Home from './pages/home'
import Login from './pages/login'
import Register from './pages/register'
import Worksheets from './pages/worksheets'
import Worksheet from './pages/worksheet'

const Router = () => {
  return <BrowserRouter>
    <Routes>
      <Route path="/" element={<Home/>}/>
      <Route path="/login" element={<Login/>}/>
      <Route path="/register" element={<Register/>}/>
      <Route path="/worksheets" element={<Worksheets/>}/>
      <Route path="/worksheet/:id" element={<Worksheet/>}/>
    </Routes>
  </BrowserRouter>
}

export default Router