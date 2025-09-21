# Performance MCP Server 🚀

A powerful Model Context Protocol (MCP) server designed for **Performance QA automation engineers** working with Vast Data features. This server provides comprehensive tools for managing performance testing workflows, including Jenkins integration, Git operations, database queries, and Google Sheets data extraction.

## 🎯 Features

- **Jenkins Integration**: Trigger jobs, extract job results, and get unique job identifiers
- **Git Operations**: Compare commits, get commit diffs, and retrieve commit lists
- **Database Queries**: Fetch performance test data from PostgreSQL databases
- **Google Sheets Integration**: Extract and analyze data from Google Sheets
- **Performance Testing**: Specialized tools for Vast Data performance testing workflows

## 📋 Prerequisites

- **Python 3.11+** (required)
- **uv** package manager (recommended for fast dependency management)
- Access to Jenkins instance
- PostgreSQL database connection
- Google Sheets API credentials (optional)

## 🚀 Installation

### Option 1: Using uv (Recommended)

1. **Install uv** (if not already installed):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd performance_mcp
   ```

3. **Install dependencies with uv**:
   ```bash
   uv sync
   ```

4. **Activate the virtual environment**:
   ```bash
   source .venv/bin/activate  # On Unix/macOS
   # or
   .venv\Scripts\activate     # On Windows
   ```

### Option 2: Using pip

1. **Create a virtual environment**:
   ```bash
   python3.11 -m venv venv
   source venv/bin/activate  # On Unix/macOS
   # or
   venv\Scripts\activate     # On Windows
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root with the following variables:

```bash
# Database Configuration
DB_HOST=your_postgres_host
DB_PORT=5432
DB_NAME=your_database_name
DB_USER=your_username
DB_PASSWORD=your_password

# Jenkins Configuration
JENKINS_URL=https://your-jenkins-instance.com
JENKINS_PORT=8080
JENKINS_USERNAME=your_username
JENKINS_API_TOKEN=your_api_token

# Git/GitLab Configuration
LOCAL_REPO_PATH=/path/to/local/repo
GITLAB_URL=https://gitlab.com/your-org/your-repo.git
GITLAB_TOKEN=your_gitlab_token

# Google Sheets Configuration (Optional)
GOOGLE_SERVICE_ACCOUNT_JSON=/path/to/credentials.json
```

### Google Sheets Setup (Optional)

1. **Enable Google Sheets API**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing one
   - Enable the Google Sheets API
   - Create credentials (Service Account or OAuth 2.0)

2. **Download credentials**:
   - Save the JSON file to your project directory
   - Update the `GOOGLE_SERVICE_ACCOUNT_JSON` in your `.env` file

## 🏃‍♂️ Running the Server

### Start the MCP Server

```bash
# Using uv
uv run python server.py

# Or activate venv first, then run
source .venv/bin/activate
python server.py
```

The server will start and be ready to accept MCP connections.

### Integration with MCP Clients

Add this server to your MCP client configuration (e.g., Cursor, Claude Desktop):

```json
{
  "mcpServers": {
    "performance-mcp": {
      "command": "python",
      "args": ["/path/to/performance_mcp/server.py"],
      "env": {
        "PYTHONPATH": "/path/to/performance_mcp",
        "DB_HOST": "your_postgres_host",
        "DB_PORT": "5432",
        "DB_NAME": "your_database_name",
        "DB_USER": "your_username",
        "DB_PASSWORD": "your_password",
        "JENKINS_URL": "https://your-jenkins-instance.com",
        "JENKINS_PORT": "8080",
        "JENKINS_USERNAME": "your_username",
        "JENKINS_API_TOKEN": "your_api_token",
        "LOCAL_REPO_PATH": "/path/to/local/repo",
        "GITLAB_URL": "https://gitlab.com/your-org/your-repo.git",
        "GITLAB_TOKEN": "your_gitlab_token",
        "GOOGLE_SERVICE_ACCOUNT_JSON": "/path/to/credentials.json"
      }
    }
  }
}
```

You can also add all the environment variables to the json for the mcp clients



## 🧪 Development

### Project Structure

```
performance_mcp/
├── pysrc/
│   ├── db_utils.py          # Database utilities
│   ├── git_tools.py         # Git operations
│   ├── jenkins.py           # Jenkins integration
│   └── sheets_utils.py      # Google Sheets integration
├── server.py                # Main MCP server
├── pyproject.toml           # Project configuration
├── requirements.txt         # Dependencies
└── README.md               # This file
```

### Adding New Tools

1. **Define the tool function** in `server.py`:
   ```python
   @mcp.tool
   async def your_new_tool(param1: str, ctx: Context) -> str:
       """Your tool description"""
       # Implementation here
       pass
   ```

2. **Access resources** through the context:
   ```python
   db_instance = ctx.request_context.lifespan_context.db
   jenkins_instance = ctx.request_context.lifespan_context.jenkins
   ```

3. **Test your tool** by running the server and using an MCP client

## 🔧 Troubleshooting

### Common Issues

1. **Database Connection Failed**:
   - Verify your PostgreSQL credentials in `.env`
   - Ensure the database server is accessible
   - Check firewall settings

2. **Jenkins Authentication Error**:
   - Verify your Jenkins URL, username, and token
   - Ensure your Jenkins user has appropriate permissions

3. **Google Sheets API Error**:
   - Check your credentials file path
   - Ensure the Google Sheets API is enabled
   - Verify the service account has access to the sheets

4. **Python Version Issues**:
   - Ensure you're using Python 3.11 or higher
   - Check your virtual environment activation


## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📞 Support

For issues and questions:
- Create an issue in the repository
- Contact the Performance QA team
- Check the troubleshooting section above

---

**Happy Performance Testing! 🎯**
