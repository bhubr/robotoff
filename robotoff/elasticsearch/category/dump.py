import hashlib
import json
from typing import Iterable, Tuple, Dict

from robotoff.insights._enum import InsightType
from robotoff.taxonomy import TAXONOMY_STORES, Taxonomy
from robotoff.utils import get_logger
from robotoff.utils.es import get_es_client, perform_export
from robotoff import settings

logger = get_logger()


SUPPORTED_LANG = {
    'fr',
    'en',
    'es',
    'de',
}


def category_export():
    logger.info("Starting category export to Elasticsearch...")
    client = get_es_client()
    category_taxonomy: Taxonomy = TAXONOMY_STORES[InsightType.category.name].get()
    logger.info("Deleting existing categories...")
    delete_categories(client)
    logger.info("Starting export...")
    category_data = generate_category_data(category_taxonomy)
    rows_inserted = perform_export(client, category_data, settings.ELASTICSEARCH_CATEGORY_INDEX)
    logger.info("%d rows inserted" % rows_inserted)


def generate_category_data(category_taxonomy: Taxonomy) -> Iterable[Tuple[str, Dict]]:
    for category_node in category_taxonomy.iter_nodes():
        supported_langs = [lang for lang in category_node.names
                           if lang in SUPPORTED_LANG]

        data = {
            f"{lang}:name": category_node.names[lang]
            for lang in supported_langs
        }
        data['id'] = category_node.id

        id_ = hashlib.sha256(category_node.id.encode('utf-8')).hexdigest()

        yield id_, data


def delete_categories(client):
    body = {"query": {"match_all": {}}}
    client.delete_by_query(body=body,
                           index=settings.ELASTICSEARCH_CATEGORY_INDEX,
                           doc_type=settings.ELASTICSEARCH_TYPE)


def insert_batch(client, batch: Iterable[Tuple[dict, dict]]):
    body = ""
    for action, source in batch:
        body += "{}\n{}\n".format(json.dumps(action),
                                  json.dumps(source))

    client.bulk(body=body,
                index=settings.ELASTICSEARCH_CATEGORY_INDEX,
                doc_type=settings.ELASTICSEARCH_TYPE)


if __name__ == "__main__":
    category_export()