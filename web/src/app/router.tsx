import { createBrowserRouter } from 'react-router-dom'
import { Landing } from '../routes/Landing'
import { SetupConfirm } from '../routes/SetupConfirm'
import { SetupPhase } from '../routes/SetupPhase'
import { SetupRun } from '../routes/SetupRun'
import { SetupStart } from '../routes/SetupStart'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Landing />,
  },
  {
    path: '/setup',
    element: <SetupStart />,
  },
  {
    path: '/setup/phase/:phase',
    element: <SetupPhase />,
  },
  {
    path: '/setup/confirm',
    element: <SetupConfirm />,
  },
  {
    path: '/setup/run',
    element: <SetupRun />,
  },
])
