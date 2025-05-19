# Ontogent

[![Coverage Status](https://coveralls.io/repos/github/gabdank/ontogent/badge.svg?branch=main)](https://coveralls.io/github/gabdank/ontogent?branch=main)

## Project Overview

Ontogent is an AI-powered tool that helps researchers and scientists find the most suitable term in the UBERON ontology for their biological samples. The agent leverages Claude 3.5 (via Anthropic API) to process natural language descriptions and return precise UBERON terms.

UBERON (Uber-anatomy ontology) is a comprehensive cross-species anatomy ontology that covers anatomical structures in animals.

## Installation

### Prerequisites

- Python 3.9+
- Anthropic API key

### Setup with Conda (Recommended)

1. Make sure you have [Miniconda](https://docs.conda.io/en/latest/miniconda.html) or [Anaconda](https://www.anaconda.com/download/) installed.

2. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/ontogent.git
   cd ontogent
   ```

3. Create and activate the conda environment:
   ```bash
   # Create the environment
   ./setup_env.sh
   
   # Activate the environment
   conda activate ontogent
   
   # Install the package in development mode
   pip install -e .
   ```

4. Set up environment variables:
   ```bash
   export ANTHROPIC_API_KEY="your_api_key_here"
   ```

### Setup with Rye (Alternative)

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/ontogent.git
   cd ontogent
   ```

2. Set up virtual environment with Rye:
   ```bash
   rye sync
   ```

3. Set up environment variables:
   ```bash
   export ANTHROPIC_API_KEY="your_api_key_here"
   ```

### Configure Environment Variables

The application supports configuration through environment variables or a `.env` file in the project root. 

Create a `.env` file with the following settings:

```
# API Keys
ANTHROPIC_API_KEY=your_api_key_here

# LLM Configuration (optional - these have defaults)
LLM_MODEL_NAME=claude-3-5-sonnet-20240620
LLM_MAX_TOKENS=4000
LLM_TEMPERATURE=0.1

# UBERON API Configuration (optional - these have defaults)
UBERON_API_BASE_URL=https://www.ebi.ac.uk/ols4/api
UBERON_API_SEARCH_ENDPOINT=/search
UBERON_API_TERM_ENDPOINT=/terms
UBERON_API_TIMEOUT=30
UBERON_API_MAX_RETRIES=3
```

## Usage

```python
from ontogent.src.services.agent import UberonAgent

# Initialize the agent
agent = UberonAgent()

# Query for a UBERON term
result = agent.find_term("liver tissue from a mouse embryo")
print(result)
```

### Command Line Interface

The application can also be used from the command line:

```bash
# Interactive mode
python src/main.py

# Single query mode
python src/main.py "heart tissue"

# With logging options
python src/main.py --log-level DEBUG --log-file ontogent.log "liver"
```

## Development Guide

### Project Structure

```
ontogent/
├── src/
│   ├── models/      # Data models using Pydantic
│   ├── services/    # Core services (LLM, UBERON)
│   ├── tools/       # Utility tools and scripts
│   ├── utils/       # Helper functions
│   └── config.py    # Configuration management
├── tests/           # Unit tests
├── docs/            # Documentation
├── pyproject.toml   # Project configuration
└── README.md        # Project documentation
```

### UBERON API Integration

The application connects to the UBERON ontology through the EBI OLS4 API. The default configuration points to the public EBI OLS4 API endpoint, but you can customize it through environment variables.

For custom API integration, implement the following in `.env` file:

```
UBERON_API_BASE_URL=your_custom_api_url
UBERON_API_SEARCH_ENDPOINT=your_custom_search_endpoint
UBERON_API_TERM_ENDPOINT=your_custom_term_endpoint
```

For alternative API endpoints, you may need to update the parsing logic in `src/services/uberon.py` to match your API's response format.

### API Troubleshooting

The EBI OLS4 API occasionally experiences connectivity or response format issues. The application includes tools to help diagnose and resolve these problems:

#### Checking API Status

Use the included API check tool to verify the EBI OLS4 API is accessible and functioning correctly:

```bash
# Run the API check tool
./src/tools/check_api.sh

# For JSON output
./src/tools/check_api.sh --format json

# With custom timeout (in seconds)
./src/tools/check_api.sh --timeout 15
```

This tool will:
1. Verify API endpoints are accessible
2. Check if responses are valid JSON
3. Validate response structure
4. Provide recommendations for configuration

If the API is not accessible or returning invalid responses, the tool will display error information and recommendations.

#### API Response Debugging

For detailed debugging of API responses, enable DEBUG-level logging:

```bash
python src/main.py --log-level DEBUG --log-file ontogent_debug.log "heart"
```

This will log the full API request and response details, which can be helpful when diagnosing API integration issues.

### Running Tests

```bash
pytest
```

## License

MIT