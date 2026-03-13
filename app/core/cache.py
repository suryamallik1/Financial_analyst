from google.cloud import bigquery
from typing import Dict, Any, Optional
import json
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class CacheClient:
    """
    Client for caching historical backtest results and external API responses in BigQuery.
    """
    def __init__(self):
        # Assumes GOOGLE_APPLICATION_CREDENTIALS is set in environment
        try:
            self.client = bigquery.Client(project=settings.GCP_PROJECT_ID)
            self.dataset_id = f"{settings.GCP_PROJECT_ID}.{settings.BIGQUERY_DATASET}"
            self._ensure_dataset_exists()
        except Exception as e:
            logger.warning(f"Could not initialize BigQuery client: {e}. Caching will be disabled.")
            self.client = None

    def _ensure_dataset_exists(self):
        if not self.client:
            return
            
        dataset = bigquery.Dataset(self.dataset_id)
        dataset.location = "US"
        try:
            self.client.create_dataset(dataset, exists_ok=True)
            self._ensure_tables_exist()
        except Exception as e:
            logger.error(f"Failed to create/verify dataset {self.dataset_id}: {e}")
            
    def _ensure_tables_exist(self):
        # Table schema for generic API response cache
        schema = [
            bigquery.SchemaField("service", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("cache_key", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("response_json", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("created_at", "TIMESTAMP", mode="REQUIRED", default_value_expression="CURRENT_TIMESTAMP()"),
        ]
        table_id = f"{self.dataset_id}.api_cache"
        table = bigquery.Table(table_id, schema=schema)
        self.client.create_table(table, exists_ok=True)

    async def get_cached_response(self, service: str, cache_key: str) -> Optional[Any]:
        """
        Retrieves a cached JSON response for a given service and key.
        """
        if not self.client:
            return None
            
        query = f"""
            SELECT response_json 
            FROM `{self.dataset_id}.api_cache` 
            WHERE service = @service AND cache_key = @cache_key
            ORDER BY created_at DESC
            LIMIT 1
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("service", "STRING", service),
                bigquery.ScalarQueryParameter("cache_key", "STRING", cache_key)
            ]
        )
        
        try:
            query_job = self.client.query(query, job_config=job_config)
            results = query_job.result()
            
            for row in results:
                return json.loads(row.response_json)
                
            return None
        except Exception as e:
            logger.error(f"Error reading from api_cache: {e}")
            return None

    async def set_cached_response(self, service: str, cache_key: str, data: Any):
        """
        Stores any serializable data as JSON string in the api_cache.
        """
        if not self.client:
            return
            
        table_id = f"{self.dataset_id}.api_cache"
        rows_to_insert = [
            {
                "service": service, 
                "cache_key": cache_key, 
                "response_json": json.dumps(data)
            }
        ]
        
        try:
            errors = self.client.insert_rows_json(table_id, rows_to_insert)
            if errors:
                logger.error(f"Errors occurred while caching to BigQuery: {errors}")
        except Exception as e:
             logger.error(f"Error writing to api_cache: {e}")
