import datetime
import operator
from typing import Dict, Iterable, Optional

from robotoff.elasticsearch.category.match import predict_category
from robotoff.insights import InsightType
from robotoff.insights.dataclass import ProductInsights, RawInsight
from robotoff.products import ProductDataset
from robotoff.utils import get_logger
from robotoff.utils.es import get_es_client

logger = get_logger(__name__)


def predict(client, product: Dict) -> Optional[ProductInsights]:
    predictions = []

    for lang in product.get("languages_codes", []):
        product_name = product.get("product_name_{}".format(lang))

        if not product_name:
            continue

        prediction = predict_category(client, product_name, lang)

        if prediction is None:
            continue

        category, score = prediction
        predictions.append((lang, category, product_name, score))
        continue

    if predictions:
        # Sort by descending score
        sorted_predictions = sorted(
            predictions, key=operator.itemgetter(2), reverse=True
        )

        p = sorted_predictions[0]
        lang, category, product_name, score = p

        return ProductInsights(
            barcode=product["code"],
            type=InsightType.category,
            insights=[
                RawInsight(
                    type=InsightType.category,
                    value_tag=category,
                    data={
                        "lang": lang,
                        "product_name": product_name,
                        "model": "matcher",
                    },
                )
            ],
        )

    return None


def predict_from_product(product: Dict) -> Optional[ProductInsights]:
    client = get_es_client()
    return predict(client, product)


def predict_from_iterable(
    client, products: Iterable[Dict]
) -> Iterable[ProductInsights]:
    for product in products:
        prediction = predict(client, product)

        if prediction:
            yield prediction


def predict_from_dataset(
    dataset: ProductDataset, from_datetime: Optional[datetime.datetime] = None
) -> Iterable[ProductInsights]:
    """Return an iterable of category insights, using the provided dataset.

    Args:
        dataset: a ProductDataset
        from_datetime: datetime threshold: only keep products modified after
            `from_datetime`
    """
    product_stream = (
        dataset.stream()
        .filter_nonempty_text_field("code")
        .filter_nonempty_text_field("product_name")
        .filter_empty_tag_field("categories_tags")
        .filter_nonempty_tag_field("countries_tags")
        .filter_nonempty_tag_field("languages_codes")
    )

    if from_datetime:
        product_stream = product_stream.filter_by_modified_datetime(
            from_t=from_datetime
        )

    product_iter = product_stream.iter()
    logger.info("Performing prediction on products without categories")

    es_client = get_es_client()
    yield from predict_from_iterable(es_client, product_iter)
