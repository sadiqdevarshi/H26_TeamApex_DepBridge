# H26_Teamapex_KJSCE
K J soumaiya Hacktober 

## DepBridge service and delivery layer

FastAPI service, a thin CLI, persistent analysis/verification state, and Dependency Exit Capsule export. Use Python 3.12 or 3.13. Backend runtime dependencies include the agreed `packaging` and `google-genai`; verification dependencies are an optional extra.

See [service startup and frontend connection](depbridge_service/README.md), [engine adapter contract](depbridge_service/ENGINE_CONTRACT.md), and [DigitalOcean setup](deployment/README.md).

The engine and frontend are developed separately. Until `depbridge_engine` is available, the running API explicitly reports `not_implemented`; it never manufactures findings, completed analyses, patches or passing tests.
