import { useState } from "react";

import Upload from "./components/Upload";
import ProgressPoller from "./components/ProgressPoller";
import RetentionChart from "./components/RetentionChart";
import WeakSegments from "./components/WeakSegments";
import SuggestionCards from "./components/SuggestionCards";
import ScoreGauge from "./components/ScoreGauge";

export default function App() {
  const [state] = useState("idle");
  const [job_id] = useState("");

  if (state === "idle") {
    return <Upload />;
  }

  if (state === "processing") {
    return <ProgressPoller />;
  }

  if (state === "results") {
    return (
      <div>
        <ScoreGauge />
        <RetentionChart />
        <WeakSegments />
        <SuggestionCards />
      </div>
    );
  }

  return <div>Invalid state: {job_id}</div>;
}
