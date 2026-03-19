import React from "react";
import { Link } from "react-router-dom";

const GraphCard: React.FC<{ title: string }> = ({ title }) => {
  return (
    <div className="bg-gray-900 rounded-lg p-4 flex flex-col shadow-md">
      <h3 className="text-sm font-semibold text-gray-300 mb-2">
        {title}
      </h3>

      {/* Graph area fills card */}
      <div className="flex-1 flex items-center justify-center border border-dashed border-gray-700 rounded">
        <span className="text-gray-500 text-xs">
          Graph goes here
        </span>
      </div>
    </div>
  );
};

const Terminal: React.FC = () => {
  return (
    <div className="bg-black rounded-lg p-4 shadow-md font-mono text-sm text-green-400 h-full overflow-y-auto">
      <div className="text-gray-400 mb-2">
        terminal@system:~$
      </div>

      <div className="space-y-1">
        <div> Initializing system...</div>
        <div> Fetching metrics...</div>
        <div> CPU usage: 42%</div>
        <div> Memory usage: 68%</div>
        <div className="text-yellow-400">
           Warning: latency spike detected
        </div>
        <div> Process completed ✔</div>
      </div>
    </div>
  );
};

const Dashboard: React.FC = () => {
  return (
    <div className="h-screen w-screen bg-gray-950 text-white flex flex-col p-4 gap-4">
      {/* Header */}
      <header className="shrink-0">
        <h1 className="text-xl font-bold">
          Data Dashboard
        </h1>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex flex-col gap-4">
        {/* Graphs Row */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 flex-1">
          <GraphCard title="Requests / Minute" />
          <GraphCard title="CPU Usage" />
          <GraphCard title="Memory Usage" />
        </div>

        {/* Terminal */}
        <div className="flex-1">
          <Terminal />
        </div>
        <Link to="/">Go to Home</Link>
      </div>
    </div>
  );
};

export default Dashboard;
