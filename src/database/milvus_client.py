import yaml
from pymilvus import (
    connections,
    Collection,
    CollectionSchema,
    FieldSchema,
    DataType,
    list_collections,
    drop_collection,
)
from .base_adapter import DatabaseAdapter


class MilvusClient(DatabaseAdapter):
    def __init__(
            self,
            config_file,
            collection_name,
            vector_dim,
            additional_fields=None,
            index_params=None,
    ):
        """Initializes a Milvus client for vector database operations.

        Args:
            config_file (str): Path to the YAML configuration file.
            collection_name (str): Name of the Milvus collection to be used or created.
            vector_dim (int): Dimension of the vectors stored in the collection.
            additional_fields (list, optional): Additional fields for the collection schema.
        """
        self._load_config(config_file)
        self.collection_name = collection_name
        self.vector_dim = vector_dim
        self.additional_fields = additional_fields if additional_fields else []
        self.index_params = (
            index_params
            if index_params
            else {
                "index_type": "IVF_FLAT",
                "metric_type": "L2",
                "params": {"nlist": 1024},
            }
        )
        self._connect()
        self._create_collection()

    def add(self, vector, metadata, check_dup=False):
        """Adds a vector and its associated metadata to the collection.

        Args:
            vector (list[float]): The vector to be added.
            metadata (dict): Metadata associated with the vector.
            check_dup (bool): Flag to check for duplicates before insertion (currently not implemented).
        """
        data = [vector] + [metadata[field] for field in metadata]
        self.collection.insert(data)
        self.collection.flush()  # Ensures data persistence

    def search(
            self,
            vector,
            top_k,
            distance_range=None,
            search_params=None,
            output_fields=None,
            filter_expr=None,
    ):
        """Performs a vector search in the collection.

        Args:
            vector (list[float]): The query vector.
            top_k (int): Number of top results to return.
            distance_range (list[int, int], optional): Minimum and maximum distances for filtering results.
            search_params (dict, optional): Parameters for the search.
            output_fields (list, optional): Fields to include in the returned results.
            filter_expr (str, optional): Filter expression for conditional search.

        Returns:
            SearchResult: Search results from Milvus.
        """
        self.collection.load()
        if search_params is None:
            search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
        if distance_range:
            search_params["params"].update(
                {"range_filter": distance_range[0], "radius": distance_range[1]}
            )

        return self.collection.search(
            data=[vector],
            anns_field="vector",
            param=search_params,
            limit=top_k,
            expr=filter_expr,
            output_fields=output_fields,
        )

    def reset(self):
        """Drops the current collection and creates a new one."""
        self.reset_collection()

    def reset_collection(self):
        """Drops the current collection and creates a new one."""
        if self.collection_name in list_collections():
            drop_collection(self.collection_name)
        self._create_collection()

    def _load_config(self, config_file):
        """Loads configuration settings from a YAML file."""
        with open(config_file, "r") as file:
            self.config = yaml.safe_load(file)

    def _connect(self, secure: bool = True):
        """Connects to the Milvus server using loaded configuration."""
        # Connect using only the non-None configuration parameters
        connections.connect(**{k: v for k, v in self.config.items() if v is not None}, )

    def _create_collection(
            self, **kwargs
    ):  # add ability to enable enable_dynamic_field and other Collection params
        """Creates a new collection in Milvus or loads an existing one."""
        if self.collection_name not in list_collections():
            fields = [
                         FieldSchema(
                             name="id", dtype=DataType.INT64, is_primary=True, auto_id=True
                         ),
                         FieldSchema(
                             name="vector", dtype=DataType.FLOAT_VECTOR, dim=self.vector_dim
                         ),
                     ] + [
                         FieldSchema(
                             name=field["name"],
                             dtype=field["dtype"],
                             max_length=field.get("max_length"),
                         )
                         for field in self.additional_fields
                     ]
            schema = CollectionSchema(
                fields, "Vector collection with additional metadata"
            )
            self.collection = Collection(name=self.collection_name, schema=schema)
            self._create_index()
        else:
            self.collection = Collection(name=self.collection_name)

    def _print_collection_schema(self):
        """Prints the schema of the current collection."""
        if self.collection_name in list_collections():
            collection = Collection(name=self.collection_name)
            print(f"Schema for collection '{self.collection_name}':")
            for field in collection.schema.fields:
                print(
                    f"Field Name: {field.name}, Data Type: {field.dtype}, Description: {field.description}"
                )
        else:
            print(f"Collection '{self.collection_name}' does not exist.")

    def _create_index(self, index_params=None):
        """Creates an index for efficient search in the collection."""
        self.collection.create_index(
            field_name="vector", index_params=self.index_params
        )
