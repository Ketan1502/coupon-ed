from google.cloud import firestore
import os


COLL = os.environ.get("FIRESTORE_COLLECTION", "coupons")
client = firestore.Client()


def save_coupon(doc: dict):
coll = client.collection(COLL)
coll.document(doc["coupon_id"]).set(doc)


def query_coupons_by_ids(ids: list):
coll = client.collection(COLL)
docs = []
for _id in ids:
d = coll.document(_id).get()
if d.exists:
docs.append(d.to_dict())
return docs