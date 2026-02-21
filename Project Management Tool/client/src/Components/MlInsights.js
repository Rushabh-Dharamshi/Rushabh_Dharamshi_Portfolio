import React from 'react';
import { Button, Spinner } from 'react-bootstrap';

function MlInsights({ riskData, onRefresh, loading }) {
  const topRisk = riskData?.top_risk || [];

  return (
    <section className="panel-card">
      <div className="panel-header row-inline">
        <div>
          <h3>ML Risk Engine</h3>
          <p>Worker-thread scoring with local heuristics, no paid model APIs.</p>
        </div>
        <Button onClick={onRefresh} className="primary-btn" disabled={loading}>
          {loading ? <Spinner size="sm" animation="border" /> : 'Refresh Risk'}
        </Button>
      </div>

      {!topRisk.length && <p className="empty-state">No risk data yet.</p>}

      <div className="risk-list">
        {topRisk.map((task) => (
          <div key={task.id} className="risk-item">
            <div>
              <strong>#{task.id} {task.title}</strong>
              <p>{task.ml_risk.recommendation}</p>
            </div>
            <div className={`risk-badge ${task.ml_risk.label}`}>
              {task.ml_risk.label} {task.ml_risk.score}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

export default MlInsights;
