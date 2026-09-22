import React from 'react'
import ReactDOM from 'react-dom/client'
import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import Shell from './components/layout/Shell'
import CommandCenter from './pages/CommandCenter'
import InvestigationQueue from './pages/InvestigationQueue'
import ProjectIntelligence from './pages/ProjectIntelligence'
import { CaseDetail, CasesList } from './pages/Cases'
import DataScreen from './pages/Data'
import './index.css'

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
    ],
  },
])

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>,
)
