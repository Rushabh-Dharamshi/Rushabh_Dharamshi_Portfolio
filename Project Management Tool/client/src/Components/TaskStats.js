import React, { useEffect, useMemo, useState } from 'react';
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

const LINE_COLORS = [
  '#0f766e',
  '#2563eb',
  '#f59e0b',
  '#ef4444',
  '#7c3aed',
  '#06b6d4',
  '#84cc16',
  '#ec4899',
  '#334155',
  '#dc2626',
];

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

function buildVelocityDatasets(categories, trend) {
  if (categories.length > 0) {
    return categories.map((series, index) => {
      const color = LINE_COLORS[index % LINE_COLORS.length];
      return {
        label: series.category,
        data: series.completed_count || [],
        borderColor: color,
        backgroundColor: `${color}33`,
        tension: 0.25,
        fill: false,
        borderWidth: 2,
        pointRadius: 2,
      };
    });
  }

  return [
    {
      label: 'Completed',
      data: trend.map((row) => row.completed_count),
      borderColor: '#0f766e',
      backgroundColor: 'rgba(15, 118, 110, 0.22)',
      tension: 0.25,
      fill: false,
      borderWidth: 2,
      pointRadius: 2,
    },
  ];
}

function TaskStats({ analytics, scopeLabel }) {
  const category = toDataset(analytics?.category, 'No Data');
  const status = toDataset(analytics?.status, 'No Data');
  const trend = analytics?.completedTrend || [];
  const velocity = analytics?.completionVelocityByCategory || { days: [], categories: [] };
  const workload = analytics?.workload || [];

  const [selectedVelocityCategory, setSelectedVelocityCategory] = useState('all');

  const velocityCategoryOptions = useMemo(
    () => (velocity.categories || []).map((item) => item.category),
    [velocity.categories]
  );

  useEffect(() => {
    if (selectedVelocityCategory !== 'all' && !velocityCategoryOptions.includes(selectedVelocityCategory)) {
      setSelectedVelocityCategory('all');
    }
  }, [selectedVelocityCategory, velocityCategoryOptions]);

  const velocityLabels = velocity.days?.length > 0
    ? velocity.days
    : trend.map((row) => row.day);

  const filteredVelocityCategories = selectedVelocityCategory === 'all'
    ? (velocity.categories || [])
    : (velocity.categories || []).filter((item) => item.category === selectedVelocityCategory);

  const velocityDatasets = buildVelocityDatasets(filteredVelocityCategories, trend);

  const workloadRows = Array.isArray(workload) ? workload : [];

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

      <article className="panel-card chart-card wide velocity-card">
        <div className="row-inline velocity-header">
          <h3>Completion Velocity (Past 14 Days, Ending Today)</h3>
          <select
            className="field-input velocity-select"
            value={selectedVelocityCategory}
            onChange={(event) => setSelectedVelocityCategory(event.target.value)}
          >
            <option value="all">All Categories</option>
            {velocityCategoryOptions.map((item) => (
              <option key={item} value={item}>{item}</option>
            ))}
          </select>
        </div>
        <div className="velocity-chart-wrap">
          <Line
            data={{
              labels: velocityLabels,
              datasets: velocityDatasets,
            }}
            options={{
              responsive: true,
              maintainAspectRatio: false,
              plugins: {
                legend: { position: 'bottom' },
              },
              scales: {
                y: {
                  beginAtZero: true,
                  ticks: {
                    precision: 0,
                  },
                },
              },
            }}
          />
        </div>
      </article>

      <article className="panel-card chart-card wide">
        <h3>Workload By Assignee</h3>
        {workloadRows.length ? (
          <Bar
            data={{
              labels: workloadRows.map((row) => row.assignee),
              datasets: [
                {
                  label: 'Open Tasks',
                  data: workloadRows.map((row) => Number(row.open_tasks) || 0),
                  backgroundColor: '#1d4ed8',
                },
                {
                  label: 'Avg Progress',
                  data: workloadRows.map((row) => Number(row.avg_progress) || 0),
                  backgroundColor: '#f59e0b',
                },
              ],
            }}
            options={{
              responsive: true,
              plugins: {
                legend: { position: 'bottom' },
              },
              scales: {
                y: {
                  beginAtZero: true,
                },
              },
            }}
          />
        ) : (
          <p className="empty-state">No workload data available.</p>
        )}
      </article>
    </section>
  );
}

export default TaskStats;