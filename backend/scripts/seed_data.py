"""Demo store: Nazakat Threads (fictional). SKUs referenced by tests.json - do not rename."""

STORE = {
    "slug": "nazakat-threads",
    "name": "Nazakat Threads",
    "description": "Islamabad-based Instagram clothing store: streetwear, kurtas, lawn suits and accessories.",
    "policies": {
        "delivery": "Islamabad/Rawalpindi Rs 200, other cities Rs 350, free delivery on orders of Rs 5,000 or more. Takes 2-4 working days.",
        "payment": "Cash on delivery or bank transfer.",
        "returns": "Exchange within 7 days if unused with tags. No cash refunds.",
        "support": "The seller can be reached on Instagram; this assistant is available 24/7.",
    },
    "delivery": {
        "local_cities": ["islamabad", "rawalpindi", "pindi", "isb", "rwp"],
        "local_fee": 200,
        "other_fee": 350,
        "free_over": 5000,
    },
}

S4 = lambda s, m, l, xl: {"S": s, "M": m, "L": l, "XL": xl}
FREE = lambda n: {"FREE": n}
W = lambda a, b, c, d: {"30": a, "32": b, "34": c, "36": d}

# (sku, name, category, color, price, description, tags, stock-by-size)
PRODUCTS = [
    ("HOOD-BLK-OS", "Black Oversized Hoodie", "Hoodies", "black", 2799, "Heavy fleece oversized fit hoodie.", "winter streetwear warm fleece", S4(6, 8, 4, 3)),
    ("HOOD-GRY-ZIP", "Grey Zip Hoodie", "Hoodies", "grey", 3299, "Zip-up hoodie with kangaroo pockets.", "winter zipper warm", S4(3, 5, 5, 2)),
    ("HOOD-NVY-PUL", "Navy Pullover Hoodie", "Hoodies", "navy", 2599, "Soft pullover hoodie, regular fit.", "winter warm casual", {"M": 4, "L": 4, "XL": 2}),
    ("HOOD-MAR-OS", "Maroon Oversized Hoodie", "Hoodies", "maroon", 2899, "Oversized hoodie in rich maroon.", "winter streetwear warm", S4(2, 3, 3, 0)),
    ("TEE-WHT-BSC", "White Basic Tee", "T-Shirts", "white", 899, "100% cotton crew neck tee.", "summer basic cotton", S4(10, 12, 10, 6)),
    ("TEE-BLK-BSC", "Black Basic Tee", "T-Shirts", "black", 899, "100% cotton crew neck tee.", "summer basic cotton", S4(10, 12, 10, 6)),
    ("TEE-BLK-GRP", "Black Graphic Tee", "T-Shirts", "black", 1199, "Printed graphic tee, relaxed fit.", "summer streetwear print", S4(5, 6, 6, 3)),
    ("TEE-OLV-POL", "Olive Polo Tee", "T-Shirts", "olive", 1499, "Smart casual polo, pique cotton.", "polo smart casual", {"M": 5, "L": 5, "XL": 3}),
    ("KURTA-WHT-LIN", "White Linen Kurta", "Kurtas", "white", 3499, "Breathable linen kurta for summer and Eid.", "eid summer linen traditional men", S4(3, 4, 3, 0)),
    ("KURTA-NVY-CTN", "Navy Cotton Kurta", "Kurtas", "navy", 2999, "Everyday cotton kurta, straight cut.", "traditional men cotton daily", S4(2, 5, 5, 3)),
    ("KURTA-BEI-EMB", "Beige Embroidered Kurta", "Kurtas", "beige", 4299, "Neck-embroidered kurta for occasions.", "wedding eid traditional embroidery men", {"M": 3, "L": 3, "XL": 2}),
    ("JEAN-BLU-SLM", "Blue Slim Jeans", "Jeans", "blue", 3799, "Stretch denim, slim fit.", "denim slim pants", W(3, 5, 4, 2)),
    ("JEAN-BLK-STR", "Black Straight Jeans", "Jeans", "black", 3999, "Straight fit black denim.", "denim straight pants", W(2, 4, 4, 1)),
    ("CHINO-KHK", "Khaki Chinos", "Trousers", "khaki", 3299, "Cotton twill chinos, tapered fit.", "pants smart casual office", W(3, 4, 4, 2)),
    ("LAWN-3PC-FLR", "Floral Lawn 3-Piece", "Lawn Suits", "floral", 5499, "Unstitched printed lawn shirt, dupatta and trouser.", "women summer unstitched lawn", FREE(6)),
    ("LAWN-3PC-MNT", "Mint Lawn 3-Piece", "Lawn Suits", "mint", 5299, "Unstitched embroidered lawn suit in mint.", "women summer unstitched lawn", FREE(4)),
    ("ABAYA-BLK", "Black Open Abaya", "Abayas", "black", 4599, "Light open-front abaya, soft crepe.", "women modest", {"S": 3, "M": 3, "L": 3}),
    ("SCARF-PRT", "Printed Scarf", "Accessories", "multi", 999, "Soft viscose printed scarf.", "women accessory", FREE(15)),
    ("CAP-BLK", "Black Cap", "Accessories", "black", 699, "Adjustable cotton baseball cap.", "cap hat accessory add-on", FREE(20)),
    ("CAP-WHT", "White Cap", "Accessories", "white", 699, "Adjustable cotton baseball cap.", "cap hat accessory add-on", FREE(10)),
    ("SOCKS-3PK", "Cotton Socks 3-Pack", "Accessories", "assorted", 499, "Three pairs of cotton crew socks.", "socks accessory add-on", FREE(25)),
    ("BELT-LTH", "Leather Belt", "Accessories", "brown", 1299, "Genuine leather belt, brass buckle.", "belt accessory", {"M": 6, "L": 6}),
]
