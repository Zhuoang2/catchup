import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { AppShell } from './components/AppShell'
import Generate from './pages/Generate'
import Sources from './pages/Sources'
import Settings from './pages/Settings'
import History from './pages/History'
import DigestView from './pages/DigestView'

export default function App() {
  return (
    <BrowserRouter>
      <AppShell>
        <Routes>
          <Route path="/" element={<Generate />} />
          <Route path="/sources" element={<Sources />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/digests" element={<History />} />
          <Route path="/digests/:id" element={<DigestView />} />
        </Routes>
      </AppShell>
    </BrowserRouter>
  )
}
