import React from 'react';
import { Bar, Doughnut, Line } from 'react-chartjs-2';
import {
  ArcElement,
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  Legend,
  LineElement,
  LinearScale,
  PointElement,
  Tooltip,
} from 'chart.js';

ChartJS.register(
  ArcElement,
  BarElement,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Legend
);

function toDataset(rows, fallbackLabel) {
  if (!rows || rows.length === 0) {
    return {
      labels: [fallbackLabel],
      values: [0],
    };
  }

  return {
    labels: rows.map((row) => row.label || row.project_name || row.day || 'Unknown'),
    values: rows.map((row) => row.value || row.completed_count || row.total || 0),
  };
}

function TaskStats({ analytics, scopeLabel }) {
  const category = toDataset(analytics?.category, 'No Data');
  const status = toDataset(analytics?.status, 'No Data');
  const trend = analytics?.completedTrend || [];
  const workload = analytics?.workload || [];

  return (
    <section className="dashboard-grid" aria-label="Analytics dashboard">
      <article className="panel-card chart-card wide">
        <h3>Analytics Scope</h3>
        <p>{scopeLabel || 'All Projects'}</p>
      </article>

      <article className="panel-card chart-card">
        <h3>Category Mix</h3>
        <Doughnut
          data={{
            labels: category.labels,
            datasets: [
              {
                data: category.values,
                backgroundColor: ['#0f766e', '#f59e0b', '#2563eb', '#ef4444', '#10b981', '#64748b'],
              },
            ],
          }}
        />
      </article>

      <article className="panel-card chart-card">
        <h3>Status Distribution</h3>
        <Bar
          data={{
            labels: status.labels,
            datasets: [
              {
                label: 'Items',
                data: status.values,
                backgroundColor: ['#1d4ed8', '#0f766e', '#b45309', '#475569'],
              },
            ],
          }}
          options={{
            plugins: { legend: { display: false } },
          }}
        />
      </article>

      <article className="panel-card chart-card wide">
        <h3>Completion Velocity (Last 14 Updates)</h3>
        <Line
          data={{
            labels: trend.map((row) => row.day),
            datasets: [
              {
                label: 'Completed',
                data: trend.map((row) => row.completed_count),
                borderColor: '#0f766e',
                backgroundColor: 'rgba(15, 118, 110, 0.22)',
                tension: 0.25,
                fill: true,
              },
            ],
          }}
        />
      </article>

      <article className="panel-card chart-card wide">
        <h3>Workload By Assignee</h3>
        <Bar
          data={{
            labels: workload.map((row) => row.assignee),
            datasets: [
              {
                label: 'Open Tasks',
                data: workload.map((row) => row.open_tasks),
                backgroundColor: '#1d4ed8',
              },
              {
                label: 'Avg Progress',
                data: workload.map((row) => row.avg_progress),
                backgroundColor: '#f59e0b',
              },
            ],
          }}
        />
      </article>
    </section>
  );
}

export default TaskStats;
