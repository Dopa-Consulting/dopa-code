import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Chat from "./pages/Chat";
import Jobs from "./pages/Jobs";
import Sessions from "./pages/Sessions";
import DiffViewer from "./pages/DiffViewer";
import Models from "./pages/Models";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Chat />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/chat" element={<Chat />} />
        <Route path="/jobs" element={<Jobs />} />
        <Route path="/sessions" element={<Sessions />} />
        <Route path="/jobs/:jobId/diff" element={<DiffViewer />} />
        <Route path="/models" element={<Models />} />
      </Route>
    </Routes>
  );
}
