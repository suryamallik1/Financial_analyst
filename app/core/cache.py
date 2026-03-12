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
        # Table schema for backtest results
        schema = [
            bigquery.SchemaField("cache_key", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("result_json", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("created_at", "TIMESTAMP", mode="REQUIRED", default_value_expression="CURRENT_TIMESTAMP()"),
        ]
        table_id = f"{self.dataset_id}.backtest_cache"
        table = bigquery.Table(table_id, schema=schema)
        self.client.create_table(table, exists_ok=True)

    async def get_cached_backtest(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a cached JSON result using the exact key.
        """
        if not self.client:
            return None
            
        query = f"""
            SELECT result_json 
            FROM `{self.dataset_id}.backtest_cache` 
            WHERE cache_key = @cache_key
            ORDER BY created_at DESC
            LIMIT 1
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("cache_key", "STRING", cache_key)
            ]
        )
        
        try:
            query_job = self.client.query(query, job_config=job_config)
            results = query_job.result()
            
            for row in results:
                return json.loads(row.result_json)
                
            return None
        except Exception as e:
            logger.error(f"Error reading from cache: {e}")
            return None

    async def set_cached_backtest(self, cache_key: str, data: Dict[str, Any]):
        """
        Stores result data as JSON string.
        """
        if not self.client:
            return
            
        table_id = f"{self.dataset_id}.backtest_cache"
        rows_to_insert = [
            {"cache_key": cache_key, "result_json": json.dumps(data)}
        ]
        
        try:
            errors = self.client.insert_rows_json(table_id, rows_to_insert)
            if errors:
                logger.error(f"Errors occurred while caching to BigQuery: {errors}")
        except Exception as e:
             logger.error(f"Error writing to cache: {e}")
