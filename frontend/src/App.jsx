import AppShell from './components/AppShell.jsx'
import IntakePage from './pages/IntakePage.jsx'

// For now the app shows a single page. React Router will be added when there is more than one screen.
export default function App() {
  return (
    <AppShell title="Job intake">
      <IntakePage />
    </AppShell>
  )
}
