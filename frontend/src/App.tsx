import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import MarketplacePage from './pages/Marketplace'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MarketplacePage />} />
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </BrowserRouter>
  )
}
