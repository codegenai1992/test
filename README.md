# Snowflake AI Assistant

A comprehensive, modular Python application that provides intelligent data exploration and analysis through a Streamlit interface, powered by Snowflake Cortex AI (Claude 4 Sonnet) and orchestrated using LangGraph and LangChain.

## 🌟 Features

- **Natural Language Queries**: Ask questions about your data in plain English
- **Multi-Agent Architecture**: Specialized agents for different types of analysis
- **Table Discovery**: Find relevant tables based on keywords and context
- **Trend Analysis**: Analyze production trends and time-series data
- **AI-Powered Insights**: Get intelligent explanations and suggestions
- **Interactive UI**: Modern Streamlit interface with chat functionality
- **Modular Design**: Clean, extensible architecture with proper separation of concerns

## 🏗️ Architecture

The application follows a modular, layered architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit UI Layer                       │
├─────────────────────────────────────────────────────────────┤
│                   Application Service                       │
├─────────────────────────────────────────────────────────────┤
│              LangGraph Orchestration Layer                  │
├─────────────────────────────────────────────────────────────┤
│    Table Discovery Agent  │  Trend Analysis Agent  │ ...   │
├─────────────────────────────────────────────────────────────┤
│  Processing Layer (Keywords, Normalization, Queries)       │
├─────────────────────────────────────────────────────────────┤
│     AI Integration        │      Database Layer            │
│  (Snowflake Cortex AI)    │    (Snowflake Client)          │
├─────────────────────────────────────────────────────────────┤
│                  Configuration Management                   │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Snowflake account with Cortex AI access
- Required Python packages (see `requirements.txt`)

### Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd snowflake-ai-assistant
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your Snowflake credentials
   ```

4. **Download NLTK data** (first run only):
   ```python
   import nltk
   nltk.download('punkt')
   nltk.download('stopwords')
   ```

### Configuration

Edit your `.env` file with the following required settings:

```env
# Snowflake Configuration
SNOWFLAKE_ACCOUNT=your_account.region
SNOWFLAKE_USER=your_username
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_WAREHOUSE=your_warehouse
SNOWFLAKE_DATABASE=your_database
SNOWFLAKE_SCHEMA=your_schema
SNOWFLAKE_ROLE=your_role

# Snowflake Cortex AI Configuration
CORTEX_AI_MODEL=claude-4-sonnet
CORTEX_AI_ENDPOINT=your_cortex_endpoint

# Application Configuration
APP_NAME=Snowflake AI Assistant
LOG_LEVEL=INFO
```

### Running the Application

#### Streamlit Web Interface (Recommended)
```bash
streamlit run streamlit_app.py
```

#### Command Line Interface
```bash
python src/main.py "Show me tables related to production"
```

#### Test Connections
```bash
python src/main.py
```

## 💡 Usage Examples

### Natural Language Queries

**Table Discovery:**
- "Show me tables related to train"
- "Find all tables containing customer data"
- "List tables in the sales schema"

**Trend Analysis:**
- "Show me the production trend for last FY"
- "Analyze sales performance over the past 6 months"
- "What are the trends in customer acquisition?"

**General Queries:**
- "What data is available for analysis?"
- "Help me understand the database structure"
- "Show me recent data from key tables"

### Streamlit Interface Features

1. **Chat Interface**: Natural conversation with the AI assistant
2. **Quick Analysis**: Pre-built analysis options for common tasks
3. **Advanced Mode**: Detailed configuration and debug options
4. **Session Management**: Conversation history and export capabilities
5. **Visualizations**: Automatic chart generation for trend data

## 🔧 Configuration

### Application Settings

The application uses a hierarchical configuration system:

1. **Environment Variables** (`.env` file)
2. **YAML Configuration** (`config/config.yaml`)
3. **Default Settings** (in code)

### Key Configuration Files

- `config/config.yaml`: Main application configuration
- `config/settings.py`: Configuration management and validation
- `.env`: Environment-specific settings (not in version control)

### Agent Configuration

Agents can be configured in `config/config.yaml`:

```yaml
agents:
  table_discovery:
    max_results: 50
    similarity_threshold: 0.7
  
  trend_analysis:
    time_periods: ["1M", "3M", "6M", "1Y", "2Y"]
    default_period: "1Y"
```

## 🏛️ Architecture Details

### Core Components

#### 1. Database Layer (`src/database/`)
- **SnowflakeClient**: Connection management and query execution
- **QueryBuilder**: Dynamic SQL query construction
- **Models**: Data models for database objects

#### 2. Processing Layer (`src/processing/`)
- **KeywordExtractor**: NLP-based keyword extraction
- **DataNormalizer**: Data cleaning and standardization
- **QueryProcessor**: Query analysis and intent detection

#### 3. AI Integration (`src/ai/`)
- **CortexAIClient**: Snowflake Cortex AI integration
- **PromptTemplates**: Structured prompts for different scenarios
- **ResponseParser**: AI response parsing and structuring

#### 4. Agent System (`src/agents/`)
- **BaseAgent**: Abstract base class for all agents
- **TableDiscoveryAgent**: Specialized for finding relevant tables
- **TrendAnalysisAgent**: Specialized for time-series analysis

#### 5. Orchestration (`src/orchestration/`)
- **WorkflowManager**: LangGraph-based multi-agent coordination

#### 6. Services (`src/services/`)
- **AppService**: Main application coordinator
- **QueryService**: Database and AI service wrapper

#### 7. UI Layer (`src/ui/`)
- **StreamlitApp**: Main Streamlit application
- **Components**: Reusable UI components
- **SessionManager**: Session state and conversation management

### Design Patterns

- **Dependency Injection**: Services are injected into dependent classes
- **Factory Pattern**: Agents are created through registry pattern
- **Observer Pattern**: Event-driven communication between components
- **Strategy Pattern**: Different processing strategies for different query types

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/test_database.py
pytest tests/test_agents.py
pytest tests/test_integration.py

# Run with coverage
pytest --cov=src tests/
```

### Test Structure

- `tests/test_database.py`: Database layer tests
- `tests/test_agents.py`: Agent functionality tests
- `tests/test_integration.py`: End-to-end integration tests

## 📊 Monitoring and Logging

### Logging Configuration

The application uses structured logging with configurable levels:

```python
# In config/config.yaml
logging:
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file_rotation: "1 day"
  max_file_size: "10 MB"
```

### Performance Monitoring

- Query execution times are tracked
- Agent performance metrics are logged
- Connection health is monitored

## 🚀 Deployment

### Docker Deployment

```bash
# Build the image
docker build -t snowflake-ai-assistant .

# Run the container
docker run -p 8501:8501 --env-file .env snowflake-ai-assistant
```

### Docker Compose

```bash
docker-compose up -d
```

### Environment Variables for Production

```env
# Production settings
DEBUG=False
LOG_LEVEL=WARNING
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=0.0.0.0
```

## 🔒 Security Considerations

- **Credentials**: Never commit credentials to version control
- **SQL Injection**: All queries use parameterized statements
- **Input Validation**: User inputs are validated and sanitized
- **Connection Security**: Secure connection to Snowflake
- **Error Handling**: Sensitive information is not exposed in error messages

## 🤝 Contributing

### Development Setup

1. Fork the repository
2. Create a feature branch
3. Install development dependencies: `pip install -r requirements.txt`
4. Make your changes
5. Run tests: `pytest`
6. Submit a pull request

### Code Style

- Follow PEP 8 guidelines
- Use type hints where appropriate
- Add docstrings to all public methods
- Keep functions focused and small

### Adding New Agents

1. Create a new agent class inheriting from `BaseAgent`
2. Implement required methods: `can_handle()` and `execute()`
3. Register the agent in `WorkflowManager`
4. Add configuration options to `config.yaml`
5. Write tests for the new agent

## 📚 API Reference

### Core Classes

#### AppService
Main application service for coordinating all components.

```python
app_service = AppService()
result = app_service.process_query("Show me production tables")
```

#### WorkflowManager
Orchestrates multi-agent workflows using LangGraph.

```python
workflow = WorkflowManager()
result = workflow.execute_workflow("Analyze trends")
```

#### SnowflakeClient
Handles database connections and query execution.

```python
client = SnowflakeClient()
result = client.execute_query("SELECT * FROM table LIMIT 10")
```

## 🐛 Troubleshooting

### Common Issues

1. **Connection Errors**
   - Verify Snowflake credentials in `.env`
   - Check network connectivity
   - Ensure Cortex AI is enabled in your Snowflake account

2. **NLTK Data Missing**
   ```python
   import nltk
   nltk.download('punkt')
   nltk.download('stopwords')
   ```

3. **Import Errors**
   - Ensure all dependencies are installed: `pip install -r requirements.txt`
   - Check Python path configuration

4. **Streamlit Issues**
   - Clear Streamlit cache: `streamlit cache clear`
   - Check port availability (default: 8501)

### Debug Mode

Enable debug mode for detailed logging:

```env
DEBUG=True
LOG_LEVEL=DEBUG
```

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **Snowflake** for Cortex AI and database platform
- **LangChain/LangGraph** for agent orchestration framework
- **Streamlit** for the web interface framework
- **OpenAI** for AI model inspiration and patterns

## 📞 Support

For support and questions:

1. Check the troubleshooting section above
2. Review the configuration documentation
3. Check the logs for detailed error information
4. Create an issue in the repository

---

**Built with ❄️ by the Snowflake AI Assistant Team**

