# Portfolio Analytics Agent

## Overview

The Portfolio Analytics Agent is an AI-powered system that enables natural language querying of portfolio management data. The system leverages Google's Gemini 2.5 Flash model to interpret user questions, route them to appropriate analytical tools, and generate comprehensive answers based on portfolio holdings, securities, transactions, and risk metrics.

## Architecture

The application follows a modular agent-based architecture with three core components:

### 1. Database Layer (`database.py`)
- Creates an in-memory SQLite database from CSV files
- Implements foreign key constraints and comprehensive indexing
- Provides safe query execution with read-only access
- Loads 9 tables: sectors, securities, benchmarks, portfolios, holdings, transactions, historical prices, portfolio performance, and risk metrics

### 2. Agent Core (`agent.py`)
- Implements a routing mechanism to select appropriate tools
- Orchestrates the question-answering workflow
- Uses Gemini 2.5 Flash model for routing decisions and answer generation
- Supports two execution tools: SQL query generation and sector exposure calculation

### 3. Tool System
Two specialized tools handle different analytical requirements:

**SQL Query Tool** (`tools/sql_tool.py`):
- Converts natural language questions to SQL queries using Gemini
- Validates and executes queries against the database
- Handles database queries including counts, aggregations, joins, and complex multi-step analytics
- Implements safety checks to prevent data mutation

**Exposure Calculator Tool** (`tools/exposure_tool.py`):
- Calculates sector exposure percentages for portfolios
- Analyzes only equity holdings (excludes bonds)
- Normalizes weights to generate sector breakdown
- Returns detailed exposure metrics and holding information

## Data Model

### Tables and Relationships

The database schema consists of 9 interconnected tables:

1. **sectors**: Sector classification with descriptions and industry groups
2. **securities**: Individual stocks and bonds with pricing, market cap, and sector assignment
3. **benchmarks**: Reference indices for performance comparison
4. **portfolios**: Portfolio metadata including AUM, risk level, and strategy type
5. **holdings**: Portfolio-security relationships with quantities, weights, and cost basis
6. **transactions**: Buy/sell transaction history with fees and settlement dates
7. **historical_prices**: OHLC price data with volume and adjusted close
8. **portfolio_performance**: NAV, returns (1M/3M/6M/1Y), volatility, Sharpe ratio, and drawdown
9. **risk_metrics**: VaR, CVaR, beta, correlation, tracking error, and Sortino ratio

### Data Generation

The system uses pre-generated CSV files located in the `data/` directory. These files contain:
- 13 portfolios with varying strategies (Growth, Income, Balanced, ESG, International, etc.)
- Multiple securities across Technology, Financial Services, Healthcare, Consumer, and Industrial sectors
- Historical transactions and price data
- Performance metrics and risk calculations

CSV files are loaded in foreign key dependency order to maintain referential integrity.

## Model Configuration

### Language Model
- **Model**: Google Gemini 2.5 Flash (`gemini-2.5-flash`)
- **API**: Google Generative AI SDK (`google-genai`)
- **Usage**:
  - Tool routing: Determines whether to use SQL query or exposure calculator
  - SQL generation: Converts natural language to SQL queries
  - Answer synthesis: Generates final responses from tool results

### Prompting Strategy

**Routing Prompt**: Instructs the model to select the appropriate tool based on question intent, returning structured JSON with tool name, reasoning, and parameters.

**SQL Generation Prompt**: Provides complete schema description and strict rules for generating valid, safe SELECT queries with proper CTEs, aliases, and financial calculations.

**Answer Generation Prompt**: Synthesizes natural language answers from tool results, maintaining clarity and conciseness.

## File Structure

```
Exercise_PL_AI_Engineer/
├── agent.py                    # Core agent with routing logic
├── app.py                      # Streamlit web interface
├── database.py                 # Database initialization and query execution
├── evaluate.py                 # Command-line interface for testing
├── database_schema.sql         # SQL schema with indexes
├── ground_truth_dataset.json   # Test questions with expected outputs
├── requirements.txt            # Python dependencies
├── data/                       # CSV data files
│   ├── benchmarks.csv
│   ├── historical_prices.csv
│   ├── holdings.csv
│   ├── portfolio_performance.csv
│   ├── portfolios.csv
│   ├── risk_metrics.csv
│   ├── sectors.csv
│   ├── securities.csv
│   └── transactions.csv
└── tools/                      # Analytical tools
    ├── exposure_tool.py        # Sector exposure calculator
    └── sql_tool.py             # Natural language to SQL converter
```

## Installation

### Prerequisites
- Python 3.8 or higher
- Google Gemini API key

### Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure API key:
Create a `.env` file in the project root:
```
GEMINI_API_KEY=your_api_key_here
```

Get an API key from: https://ai.google.dev/gemini-api/docs

## Usage

### Streamlit Web Interface

Launch the interactive web application:
```bash
streamlit run app.py
```

Features:
- Natural language question input
- Example questions in sidebar
- SQL query visualization for debugging
- Tabular results display
- Sector exposure charts

### Command-Line Interface

Run interactively:
```bash
python evaluate.py
```

Ask a single question:
```bash
python evaluate.py --question "How many portfolios do we have?"
```

Enable debug logging:
```bash
python evaluate.py --debug
```

## Example Questions

### SQL Query Tool
- "How many portfolios do we have in total?"
- "What are the names of all active portfolios?"
- "Which securities are in the Technology sector?"
- "Show me the top 5 holdings by cost basis in the Growth Equity Fund"
- "What is the average current price of securities in each sector?"

### Exposure Calculator Tool
- "What are the sector exposures for the Tech Innovation Fund?"
- "Calculate the sector exposure breakdown for International Equity Fund"

## Evaluation Dataset

The `ground_truth_dataset.json` file contains 10 test questions with:
- Question text
- Difficulty level (easy/medium/hard)
- Expected tool selection
- Ground truth SQL queries or parameters
- Result type and explanation

This dataset enables systematic evaluation of:
- Routing accuracy
- SQL generation quality
- Exposure calculation correctness

## Technical Implementation

### Query Safety
- Read-only database access enforced at multiple levels
- SQL validation blocks INSERT, UPDATE, DELETE, DROP operations
- Empty value coercion prevents injection through NULL handling
- Foreign key constraints maintain data integrity

### Error Handling
- Comprehensive try-catch blocks at each processing stage
- Detailed logging for debugging and monitoring
- User-friendly error messages for failed operations
- Graceful degradation when tool execution fails

### Performance Optimizations
- In-memory SQLite database for fast query execution
- 18 strategically placed indexes on frequently joined columns
- Composite indexes for common query patterns
- Connection pooling with thread-safe configuration

## Logging

Logs are written to:
- Console output (INFO level)
- `logs/agent.log` file (with rotation)

Debug mode provides verbose logging including:
- Routing decisions with reasoning
- Generated SQL queries
- Tool execution results
- API call details

## Dependencies

### Core Requirements
- `google-genai>=0.10.0`: Google Generative AI SDK for Gemini model access
- `python-dotenv>=1.0.0`: Environment variable management
- `streamlit>=1.28.0`: Web interface framework
- `pandas>=2.0.0`: Data manipulation and display
- `numpy>=1.24.0`: Numerical operations

### Optional Extensions
- `scipy>=1.10.0`: Advanced statistical calculations
- `matplotlib>=3.7.0`: Visualization capabilities
- `seaborn>=0.12.0`: Enhanced plotting

### API Development (Bonus)
- `fastapi>=0.104.0`: REST API framework
- `uvicorn>=0.24.0`: ASGI server
- `pydantic>=2.5.0`: Data validation

### Testing
- `pytest>=7.4.0`: Unit testing framework
- `httpx>=0.25.0`: API endpoint testing

## Limitations and Considerations

1. **In-Memory Database**: Data persists only during application runtime
2. **Read-Only Access**: No support for data modification operations
3. **Model Dependency**: Requires active internet connection for Gemini API
4. **Token Limits**: Large result sets may be truncated in answer generation
5. **Portfolio Name Matching**: Exposure calculator requires exact portfolio name matching

## Future Enhancements

- Persistent database storage (PostgreSQL/MySQL)
- Multi-turn conversation with context retention
- Custom portfolio creation and modification
- Real-time market data integration
- Advanced risk analytics and what-if scenarios
- RESTful API for programmatic access
- Caching layer for frequently asked questions
- Support for additional LLM providers

## License

This project is part of an AI Engineering exercise and is intended for educational and evaluation purposes.
