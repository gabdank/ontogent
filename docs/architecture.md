# Ontogent Architecture

This document explains the architecture of the Ontogent application and how its components work together to find suitable UBERON ontology terms.

## Overview

Ontogent is a system that uses AI (specifically Claude 3.5) to help users find the most suitable term in the UBERON ontology for their anatomical samples. The agent takes a natural language description from the user, uses Claude to understand the query, searches the UBERON ontology for relevant terms, and then uses Claude again to rank the results and provide the best match with an explanation.

## High-Level Architecture

The system follows a modular architecture with the following main components:

```
                  ┌─────────────┐
                  │    User     │
                  └──────┬──────┘
                         │
                         ▼
┌────────────────────────────────────────────┐
│               UberonAgent                  │
│                                            │
│  ┌──────────────┐        ┌──────────────┐  │
│  │  LLMService  │◄─────► │UberonService │  │
│  └──────────────┘        └──────────────┘  │
└────────────────────────────────────────────┘
         ▲                        ▲
         │                        │
         ▼                        ▼
┌──────────────┐        ┌──────────────────┐
│ Anthropic API│        │ UBERON Ontology  │
└──────────────┘        └──────────────────┘
```

## Key Components

### 1. Data Models (`models/`)

- `UberonTerm`: Represents a term from the UBERON ontology with properties like ID, label, definition, synonyms, and parent terms.
- `SearchQuery`: Encapsulates parameters for searching UBERON terms.
- `SearchResult`: Contains the results of a search, including matching terms, the best match, confidence score, and reasoning.

### 2. Services (`services/`)

- `LLMService`: Handles interactions with Claude 3.5 via the Anthropic API. It's responsible for:
  - Analyzing user queries to extract key anatomical concepts
  - Ranking multiple UBERON terms based on relevance to the user's query
  - Providing reasoning for term selection

- `UberonService`: Manages interactions with the UBERON ontology. It's responsible for:
  - Searching for UBERON terms based on queries
  - Retrieving detailed information about specific terms

- `UberonAgent`: The main orchestrator that coordinates between the LLM and UBERON services. It:
  - Takes a user query
  - Uses the LLM to analyze the query
  - Searches for relevant terms via the UBERON service
  - Asks the LLM to rank multiple results if needed
  - Returns the best match with explanation

### 3. Utilities (`utils/`)

- `logging_utils`: Provides utility functions for setting up logging and handling errors with rich context.

## Processing Flow

When a user asks the agent to find an UBERON term, the following process occurs:

1. **Query Understanding**:
   - The user's query is sent to the `LLMService`
   - Claude analyzes the query to identify key anatomical concepts, species information, developmental stage, etc.
   - Claude suggests potential search terms

2. **Term Search**:
   - The `UberonService` searches for UBERON terms matching the suggested search terms
   - It returns a list of potential matching terms

3. **Result Ranking** (if multiple matches):
   - The `LLMService` is used again to rank the potential matches
   - Claude evaluates each term against the original query
   - Claude selects the best match and provides a confidence score and reasoning

4. **Result Presentation**:
   - The agent returns the best matching term along with its definition, synonyms, etc.
   - It also provides Claude's reasoning for why this term is the best match

## Error Handling and Logging

The system includes comprehensive error handling and logging:

- All services include try-except blocks to catch and handle errors
- Errors are logged with detailed context information
- A custom `CustomError` class enriches exceptions with context
- The `log_exceptions` decorator can be applied to functions to automatically log and enrich exceptions

## Configuration

The application uses a centralized configuration system:

- `config.py` contains settings loaded from environment variables
- Settings are validated using Pydantic models
- Configuration includes API keys, LLM parameters, and service endpoints

## Testing

The architecture is designed for testability:

- Services have clear interfaces that can be mocked for unit testing
- The modular design allows components to be tested in isolation
- Test fixtures use unittest's mock capabilities to create controlled environments

## Future Enhancements

Potential areas for extension:

1. **Real UBERON API Integration**: Replace the mock UBERON service with a real API client
2. **Interactive Refinement**: Allow users to refine their search based on initial results
3. **Batch Processing**: Support batch processing of multiple queries
4. **Web Interface**: Add a web interface for easier interaction
5. **Result Caching**: Cache common queries for improved performance
6. **Expanded Context**: Allow users to provide additional context like research area or specific species
7. **Multilingual Support**: Support queries in multiple languages 