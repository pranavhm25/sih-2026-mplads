import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import Shell from './components/layout/Shell'
import CommandCenter from './pages/CommandCenter'
import InvestigationQueue from './pages/InvestigationQueue'
import ProjectIntelligence from './pages/ProjectIntelligence'
import { CaseDetail, CasesList } from './pages/Cases'
import DataScreen from './pages/Data'
import Stakeholders from './pages/Stakeholders'
import CagValidation from './pages/CagValidation'
import SyntheticValidation from './pages/SyntheticValidation'
import SystemStatus from './pages/SystemStatus'

const router = createBrowserRouter([
  {
    path: '/',
    element: <Shell />,
    children: [
      { index: true, element: <CommandCenter /> },
      { path: 'queue', element: <InvestigationQueue /> },
      { path: 'projects/:id', element: <ProjectIntelligence /> },
      { path: 'cases', element: <CasesList /> },
      { path: 'cases/:id', element: <CaseDetail /> },
      { path: 'data', element: <DataScreen /> },
      { path: 'stakeholders', element: <Stakeholders /> },
      { path: 'validation', element: <CagValidation /> },
      { path: 'validation/synthetic', element: <SyntheticValidation /> },
      { path: 'system', element: <SystemStatus /> },
    ],
  },
])

export default function App() {
  return <RouterProvider router={router} />
}
