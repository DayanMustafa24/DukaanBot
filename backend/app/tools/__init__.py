from .catalog import get_product, search_catalog
from .orders import get_order_status, propose_order
from .pricing import calculate_total

SALES_TOOLS = [search_catalog, get_product, calculate_total, get_order_status]
ORDER_TOOLS = [search_catalog, get_product, calculate_total, propose_order]

TOOLS_BY_NAME = {t.name: t for t in [*SALES_TOOLS, *ORDER_TOOLS]}
ALLOWED = {
    "sales": {t.name for t in SALES_TOOLS},
    "order": {t.name for t in ORDER_TOOLS},
}
