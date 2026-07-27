import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import Chat from "./pages/Chat";
import Cambios from "./pages/Cambios";
import Sessions from "./pages/Sessions";
import Models from "./pages/Models";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Chat />} />
        <Route path="/chat" element={<Chat />} />
        <Route path="/cambios" element={<Cambios />} />
        <Route path="/sessions" element={<Sessions />} />
        <Route path="/models" element={<Models />} />
      </Route>
    </Routes>
  );
}
