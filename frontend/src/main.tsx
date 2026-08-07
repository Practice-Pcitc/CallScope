import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App as AntdApp, ConfigProvider, theme } from "antd";

import { AppRouter } from "./router";
import "./styles/global.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ConfigProvider
      theme={{
        algorithm: theme.darkAlgorithm,
        token: {
          colorPrimary: "#7c6df2",
          colorInfo: "#7c6df2",
          colorBgBase: "#0b0d12",
          colorBgContainer: "#11141b",
          colorBorder: "#252a35",
          borderRadius: 10,
          fontFamily:
            "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
        }
      }}
    >
      <AntdApp>
        <AppRouter />
      </AntdApp>
    </ConfigProvider>
  </StrictMode>
);
