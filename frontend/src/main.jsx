import React from "react";
import ReactDOM from "react-dom/client";

import App from "./App.jsx";
import DeploymentRefreshNotice from "./DeploymentRefreshNotice.jsx";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <DeploymentRefreshNotice />
    <App />
  </React.StrictMode>,
);
