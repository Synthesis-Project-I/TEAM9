import { Routes, Route, BrowserRouter } from "react-router-dom"
import MainLayout from './layouts/mainLayout'

import Translators from "./app/translators/page.tsx"
import Dashboard from "./app/dashboard/page.tsx"
import Clients from "./app/clients/page.tsx"
import Tasks from "./app/tasks/page.tsx"
import QuickCreate from "./app/quickCreate/page.tsx"
import Assign from "./app/assign/page.tsx"

export default function App() {
  return (
    <Routes>
      <Route element={<MainLayout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/translators" element={<Translators />} />
        <Route path="/clients" element={<Clients />} />
        <Route path="/tasks" element={<Tasks />} />
        <Route path="/quickCreate" element={<QuickCreate />} />
        <Route path="/assign" element={<Assign />} />
      </Route >
    </Routes>
  )
}
