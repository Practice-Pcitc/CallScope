import { createBrowserRouter, Navigate, RouterProvider } from "react-router-dom";

import { AppShell } from "./components/layout/AppShell";
import { GraphPage } from "./pages/GraphPage";
import { ProjectPage } from "./pages/ProjectPage";

const router = createBrowserRouter([
  {
    element: <AppShell />,
    children: [
      { index: true, element: <Navigate to="/projects" replace /> },
      { path: "/projects", element: <ProjectPage /> },
      { path: "/projects/:projectId/graph", element: <GraphPage /> }
    ]
  }
]);

export function AppRouter() {
  return <RouterProvider router={router} />;
}

