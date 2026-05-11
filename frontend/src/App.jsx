import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Navbar from './components/Navbar'
import HomePage from './pages/HomePage'
import AnalyzePage from './pages/AnalyzePage'
import ResultsPage from './pages/ResultsPage'
import { RoofProvider } from './hooks/useRoofAnalysis'

export default function App() {
  return (
    <BrowserRouter>
      <RoofProvider>
        <div className="min-h-screen grid-pattern">
          <Navbar />
          <main>
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/upload" element={<AnalyzePage />} />
              <Route path="/results" element={<ResultsPage />} />
            </Routes>
          </main>
        </div>
      </RoofProvider>
    </BrowserRouter>
  )
}
