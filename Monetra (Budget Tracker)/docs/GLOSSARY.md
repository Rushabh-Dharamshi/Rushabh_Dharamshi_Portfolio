# Glossary

This file explains common words used in the Monetra documentation.

## App Terms

| Term | Meaning |
| --- | --- |
| Frontend | The part of the app you see in the browser. Monetra uses Next.js and React. |
| Backend | The server that stores data, validates requests, generates reports, and runs AI workflows. Monetra uses Flask. |
| Database | The place where users, expenses, budgets, recurring payments, and savings goals are stored. Monetra uses PostgreSQL. |
| API | A set of URLs the frontend calls to ask the backend to do something. |
| Health check | A simple URL that confirms the backend is running. |
| Docker | A tool for running the app services in repeatable containers. |
| Docker Compose | A Docker tool that starts several services together, such as frontend, backend, PostgreSQL, and Chroma. |

## AI Terms

| Term | Meaning |
| --- | --- |
| Ollama | Runs local AI models on your machine or server. |
| LLM | A large language model. In Monetra, `qwen2.5:7b` is used for AI answers and agent reasoning. |
| Embedding model | A model that turns text into numbers so similar text can be searched. Monetra uses `nomic-embed-text`. |
| RAG | Retrieval-Augmented Generation. The app first retrieves relevant finance data, then asks the AI to answer using that data. |
| Chroma | The vector database that stores searchable RAG embeddings. |
| Agentic AI | AI that can plan steps, use tools, check results, and return an auditable answer. |
| LangGraph | The workflow engine that manages agent planning, execution, repair, and verification. |
| MCP tools | Structured finance actions the AI can call, such as reading dashboard data or generating a report. |

## Testing And Deployment Terms

| Term | Meaning |
| --- | --- |
| Unit test | A small automated test for one function, class, or component. |
| Integration test | A test that checks several parts working together. |
| E2E test | End-to-end test. It checks the app through a browser like a user would. |
| Load test | A test that simulates many users or repeated requests. |
| Dummy user | A fake user created only for testing. |
| Chaos engineering | Controlled failure testing, such as temporarily stopping a database in staging to verify recovery. |
| Smoke check | A small check after startup or deployment to confirm the app basically works. |
| Staging | A production-like environment used for testing before production. |
| Production | The live environment users rely on. |
| CI/CD | Automated testing and deployment pipeline. Monetra uses CircleCI. |
| Manual approval gate | A CircleCI pause where a person must approve production deployment. |
