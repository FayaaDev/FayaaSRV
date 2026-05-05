import { RouterProvider } from 'react-router-dom'
import { I18nProvider } from './i18n/context'
import { router } from './app/router'
import './App.css'

function App() {
  return (
    <I18nProvider>
      <RouterProvider router={router} />
    </I18nProvider>
  )
}

export default App
