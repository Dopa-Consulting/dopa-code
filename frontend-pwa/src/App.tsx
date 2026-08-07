import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import Chat from "./pages/Chat";
import Cambios from "./pages/Cambios";
import Sessions from "./pages/Sessions";
import Models from "./pages/Models";
import PluginsPage from "./pages/PluginsPage";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Chat />} />
        <Route path="/chat" element={<Chat />} />
        <Route path="/cambios" element={<Cambios />} />
        <Route path="/sessions" element={<Sessions />} />
        <Route path="/models" element={<Models />} />
        <Route path="/plugins" element={<PluginsPage />} />
      </Route>
    </Routes>
  );
}
