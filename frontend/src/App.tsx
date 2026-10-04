import { BrowserRouter, Link, Route, Routes } from 'react-router-dom'
import Generate from './pages/Generate'
import Sources from './pages/Sources'
import Settings from './pages/Settings'
import History from './pages/History'
import DigestView from './pages/DigestView'

export default function App() {
  return (
    <BrowserRouter>
      <header>
        <h1>CatchUp</h1>
        <nav aria-label="Main">
          <Link to="/">Generate</Link>
          <Link to="/sources">Sources</Link>
          <Link to="/settings">Settings</Link>
          <Link to="/digests">History</Link>
        </nav>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<Generate />} />
          <Route path="/sources" element={<Sources />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/digests" element={<History />} />
          <Route path="/digests/:id" element={<DigestView />} />
        </Routes>
      </main>
    </BrowserRouter>
  )
}
