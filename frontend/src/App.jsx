import AppShell from './components/AppShell.jsx'
import IntakePage from './pages/IntakePage.jsx'

// For now the app shows a single page. 
export default function App() {
  return (
    <AppShell title="Job intake">
      <IntakePage />
    </AppShell>
  )
}
