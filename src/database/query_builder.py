# src/database/query_builder.py

import json
from typing import Dict, Any
from string import Template


class ElasticQueryBuilder:
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the QueryBuilder with the Elasticsearch-related config.

        Args:
            config (Dict[str, Any]): Elasticsearch config, including the query templates and other parameters.
        """
        if not config or 'query_body' not in config:
            raise ValueError("Elasticsearch config must include 'query_body'.")

        self.query_body: Dict[str, Any] = config.get('query_body')
        self.timeout: int = config.get('timeout', 30)
        self.max_retries: int = config.get('max_retries', 3)
        self.overfetch_buffer: int = config.get('overfetch_buffer', 50)

    def get_query(self, user_input: str) -> Dict[str, Any]:
        """
        Retrieve and process the query template with user input.

        Args:
            user_input (str): The user input to inject into the query.

        Returns:
            Dict[str, Any]: The processed query body.
        """
        if not self.query_body:
            raise ValueError("No query body found in the Elasticsearch configuration.")

        # Convert the query body to JSON string for template substitution
        query_body_str = json.dumps(self.query_body)

        # Escape user input properly using json.dumps
        escaped_user_input = json.dumps(user_input)[1:-1]

        # Replace placeholders using Python's Template
        processed_query_str = Template(query_body_str).substitute(USER_INPUT=escaped_user_input)

        return json.loads(processed_query_str)
