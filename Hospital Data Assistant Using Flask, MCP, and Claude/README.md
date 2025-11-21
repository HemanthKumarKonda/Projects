# Hospital Data Hospital Data Assistant Using Flask, MCP, and Claude
This project turns local hospital datasets into an intelligent, conversational assistant powered by Claude and the Model Context Protocol (MCP).

Overview

The system has three layers:

Datasets
CSV files storing patients, staff, services, and visit logs.

Flask API
A lightweight Python API that exposes dataset operations through endpoints such as:
/patients, /patient/<id>, /search_patients, /staff, /weekly_stats.

MCP Server
A Python MCP wrapper (server.py) that defines tools like:

list_datasets

search_patients

get_patient_by_id

search_staff

weekly_service_stats

Claude Desktop uses these tools to interact with the data directly.

Folder Structure
hospital-api/
│
├── data/
│   ├── patients.csv
│   ├── staff.csv
│   ├── visits.csv
│   └── services.csv
│
├── api/
│   └── app.py     # Flask API
│
└── mcp_server/
    └── server.py  # MCP wrapper

Running the Project
1. Install dependencies
pip install flask pandas fastmcp requests

2. Start the Flask API
python api/app.py

3. Start the MCP server
python mcp_server/server.py

Connecting to Claude Desktop

Add this to your local.json MCP config:

{
  "mcpServers": {
    "hospital-api": {
      "command": "python",
      "args": [
        "C:/Users/konda/hospital-api/mcp_server/server.py"
      ]
    }
  }
}


Restart Claude.
The tools will appear automatically.

Example Claude Queries

“List all datasets.”

“Search for patients whose name contains ‘an’.”

“Get details for patient with ID 4.”

“Show weekly service usage stats.”

Claude handles the tool calling automatically through MCP.

Why I Built This

To explore how AI models can interact with real, structured data systems—not just text.
It’s a complete pipeline: raw data → API → MCP → conversational interface.

