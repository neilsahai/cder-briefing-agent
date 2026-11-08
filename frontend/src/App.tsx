import { BrowserRouter, NavLink, Route, Routes } from 'react-router-dom'
import AskPage from './AskPage'
import { BriefingPage, CertifiedPage, DataHealthPage, EvalsPage, RunsPage } from './Pages'

export default function App() {
  return (
    <BrowserRouter>
      <div className="shell">
        <nav className="rail" aria-label="Main">
          <div className="brand">CDER Shortage Briefing Desk<small>Office of Drug Shortage Staff · prototype</small></div>
          <NavLink to="/" end>Ask</NavLink>
          <NavLink to="/briefing">Briefing</NavLink>
          <NavLink to="/certified">Certified queries</NavLink>
          <NavLink to="/data">Data health</NavLink>
          <NavLink to="/evals">Evals</NavLink>
          <NavLink to="/runs">Runs</NavLink>
          <div className="foot">Synthetic FDA snapshot. No real patient or manufacturer data. Answers cite source rows; nothing here is testimony until a reviewer signs it.</div>
        </nav>
        <main className="main">
          <Routes>
            <Route path="/" element={<AskPage />} />
            <Route path="/briefing" element={<BriefingPage />} />
            <Route path="/certified" element={<CertifiedPage />} />
            <Route path="/data" element={<DataHealthPage />} />
            <Route path="/evals" element={<EvalsPage />} />
            <Route path="/runs" element={<RunsPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
