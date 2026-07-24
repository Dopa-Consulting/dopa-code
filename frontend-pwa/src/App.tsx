import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Jobs from "./pages/Jobs";
import DiffViewer from "./pages/DiffViewer";
import PRViewer from "./pages/PRViewer";
import Models from "./pages/Models";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/jobs" element={<Jobs />} />
        <Route path="/jobs/:jobId/diff" element={<DiffViewer />} />
        <Route path="/jobs/:jobId/pr" element={<PRViewer />} />
        <Route path="/models" element={<Models />} />
      </Route>
    </Routes>
  );
}
