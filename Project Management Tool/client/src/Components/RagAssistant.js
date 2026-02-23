import React, { useRef, useState } from 'react';
import { Button, Form, Spinner } from 'react-bootstrap';
import { apiUrl } from '../config/api';

function RagAssistant({ assistantContext }) {
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      text: 'Ask about completed tasks, blockers, risk, workload, project summaries, or next-step recommendations.',
    },
  ]);

  const conversationIdRef = useRef(
    typeof crypto !== 'undefined' && crypto.randomUUID
      ? crypto.randomUUID()
      : `session-${Date.now()}-${Math.floor(Math.random() * 100000)}`
  );

  const sendMessage = async (event) => {
    event.preventDefault();

    if (!input.trim()) {
      return;
    }

    const question = input.trim();
    const nextMessages = [...messages, { role: 'user', text: question }];

    setInput('');
    setMessages(nextMessages);
    setLoading(true);

    try {
      const response = await fetch(apiUrl('/api/chat'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: question,
          conversation_id: conversationIdRef.current,
          context: assistantContext || {},
          recent_messages: nextMessages.slice(-6),
        }),
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(data.details || data.error || `Chat request failed (${response.status})`);
      }

      const answer = String(data.answer || '').trim() || 'No answer was returned from the assistant.';

      setMessages((prev) => [
        ...prev,
        { role: 'assistant', text: answer },
      ]);
    } catch (error) {
      setMessages((prev) => [...prev, { role: 'assistant', text: `Assistant error: ${error.message}` }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="panel-card assistant-panel">
      <div className="panel-header">
        <h3>RAG Project Assistant</h3>
        <p>Vertex AI RAG grounded on your project database with Gemini generation.</p>
      </div>

      <div className="chat-log">
        {messages.map((message, index) => (
          <div key={`${message.role}-${index}`} className={`chat-message ${message.role}`}>
            {message.text}
          </div>
        ))}
      </div>

      <Form onSubmit={sendMessage} className="chat-form">
        <Form.Control
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder="Ask a portfolio PM question"
        />
        <Button type="submit" className="primary-btn" disabled={loading}>
          {loading ? <Spinner size="sm" animation="border" /> : 'Send'}
        </Button>
      </Form>
    </section>
  );
}

export default RagAssistant;
