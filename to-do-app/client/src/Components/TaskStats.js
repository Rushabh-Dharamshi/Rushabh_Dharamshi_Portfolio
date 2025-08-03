import React from 'react';
import { Pie } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend,
} from 'chart.js';

ChartJS.register(ArcElement, Tooltip, Legend);

function TaskStats({ tasks }) {
  const groupCompletedBy = (key, options) => {
    const counts = {};

    tasks.forEach((task) => {
      if (task.is_completed) {
        let val = task[key] || 'Unspecified';

        if (key === 'due_date') {
          const dueDate = new Date(task.due_date);
          const now = new Date();
          const diffDays = Math.floor((dueDate - now) / (1000 * 60 * 60 * 24));

          if (diffDays < 0) val = 'Today';
          else if (diffDays === 0) val = 'Tomorrow';
          else if (diffDays <= 7) val = 'This Week';
          else val = 'Later';
        }

        if (!counts[val]) counts[val] = 0;
        counts[val]++;
      }
    });

    if (options && options.length > 0) {
      Object.keys(counts).forEach((k) => {
        if (!options.includes(k)) delete counts[k];
      });
    }

    return counts;
  };

  const categoryData = groupCompletedBy('category');
  const difficultyData = groupCompletedBy('difficulty_level', ['easy', 'medium', 'hard']);
  const deadlineData = groupCompletedBy('due_date', ['Past Due', 'Today', 'Tomorrow', 'This Week', 'Later']);
  const priorityData = groupCompletedBy('priority', ['high', 'medium', 'low']);

  const totalCompleted = tasks.filter((task) => task.is_completed).length;

  const getChartData = (dataObj, colors) => ({
    labels: Object.keys(dataObj),
    datasets: [
      {
        data: Object.values(dataObj),
        backgroundColor: colors,
        borderWidth: 1,
      },
    ],
  });

  const categoryColors = ['#6f42c1', '#ffc107', '#0d6efd', '#198754', '#dc3545'];
  const difficultyColors = ['#0d6efd', '#ffc107', '#dc3545'];
  const deadlineColors = ['#6c757d', '#dc3545', '#fd7e14', '#0d6efd', '#198754'];
  const priorityColors = ['#dc3545', '#ffc107', '#198754'];

  const pieOptions = {
    maintainAspectRatio: false,
    plugins: {
      legend: { position: 'bottom' },
    },
  };

  const summaryBox = (title, data, colors) => (
    <div style={summaryCardStyle}>
      <h4 style={summaryTitleStyle}>{title}</h4>
      {Object.keys(data).length === 0 ? (
        <p style={{ fontStyle: 'italic' }}>No completed tasks in this category.</p>
      ) : (
        <>
          <div style={{ height: '160px' }}>
            <Pie data={getChartData(data, colors)} options={pieOptions} />
          </div>
          <ul style={summaryListStyle}>
            {Object.entries(data).map(([key, count]) => (
              <li key={key}>
                <strong>{key}</strong>: {count}
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );

  const dashboardStyle = {
    display: 'flex',
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: '30px',
    padding: '20px',
    fontFamily: 'Arial, sans-serif',
  };

  const sidebarStyle = {
    flex: '0 0 220px',
    backgroundColor: '#f8f9fa',
    padding: '20px',
    borderRadius: '10px',
    boxShadow: '0 0 6px rgba(0,0,0,0.1)',
    fontSize: '1rem',
    fontWeight: '500',
  };

  const summaryContainerStyle = {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
    gap: '20px',
    flex: 1,
  };

  const summaryCardStyle = {
    backgroundColor: '#fff',
    padding: '16px',
    borderRadius: '10px',
    boxShadow: '0 0 8px rgba(0,0,0,0.05)',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
  };

  const summaryTitleStyle = {
    marginBottom: '10px',
    fontSize: '1.1rem',
    color: '#333',
  };

  const summaryListStyle = {
    marginTop: '10px',
    paddingLeft: '0',
    listStyle: 'none',
    textAlign: 'left',
    fontSize: '0.95rem',
    width: '100%',
  };

  return (
    <section>
      <h2 style={{ padding: '20px' }}>Task Completion Dashboard</h2>
      <div style={dashboardStyle}>
        {/* Sidebar Summary */}
        <div style={sidebarStyle}>
          <h3 style={{ marginBottom: '10px' }}>Summary</h3>
          <p><strong>Total Completed:</strong> {totalCompleted}</p>
          <hr style={{ margin: '12px 0' }} />
          <p>Includes charts for:</p>
          <ul style={{ paddingLeft: '18px', fontSize: '0.95rem' }}>
            <li>Category</li>
            <li>Difficulty</li>
            <li>Deadline</li>
            <li>Priority</li>
          </ul>
        </div>

        {/* Chart Summaries */}
        <div style={summaryContainerStyle}>
          {summaryBox('By Category', categoryData, categoryColors)}
          {summaryBox('By Difficulty', difficultyData, difficultyColors)}
          {summaryBox('By Deadline', deadlineData, deadlineColors)}
          {summaryBox('By Priority', priorityData, priorityColors)}
        </div>
      </div>
    </section>
  );
}

export default TaskStats;
