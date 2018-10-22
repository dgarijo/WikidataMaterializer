import urllib.request
import sys
import csv
import copy
import json
from typing import List
from pprint import pprint
import re


def read_args():
    property = ""
    if len(sys.argv) > 1:
        property = sys.argv[1].strip()

    return property


def formulate_main_query(property):
    main_query = 'select distinct ?source ?source_l ?category ?prop_l ?prop_value ?know_as ?id_l ?id ?id_value where{\
        ?source wdt:' + property + ' ?prop_value.\
        ?source rdfs:label ?source_l.\
        ?source wdt:P31/rdfs:label ?category.\
        filter (lang(?category)="en")\
        filter (lang(?source_l)="en")\
        wd:' + property + ' rdfs:label ?prop_l.\
        filter (lang(?prop_l)="en")\
        optional {?prop_value rdfs:label ?know_as.\
                 filter (lang(?know_as)="en")}\
        ?source ?id ?id_value.\
        ?identifier wikibase:directClaim ?id.\
        ?identifier wikibase:propertyType wikibase:ExternalId.\
        ?identifier rdfs:label ?id_l.\
        ?identifier schema:description ?desc.\
        filter (lang(?desc)="en")\
        filter (lang(?id_l)="en")\
        }'

    return main_query


def formulate_id_category_query(property):
    id_category_query = \
        'select distinct ?identifier ?l where{\
            ?source wdt:' + property + ' ?value.\
            ?source ?id ?idValue.\
            ?identifier ?ref ?id.\
            optional {?value rdfs:label ?know_as.\
            filter (lang(?know_as)="en")}\
            ?identifier wikibase:directClaim ?id.\
            ?identifier wikibase:propertyType wikibase:ExternalId.\
            ?identifier rdfs:label ?l.\
            ?identifier schema:description ?desc.\
            filter (lang(?desc)="en")\
            filter (lang(?l)="en")\
            }\
        ORDER BY ?identifier'

    return id_category_query


def encode_url(url):
    encoded_url = urllib.parse.quote(url)
    return encoded_url


def get_query_result(query_req) -> List[dict]:
    data = {}
    with urllib.request.urlopen(query_req) as r:
        data = json.loads(r.read().decode('utf-8'))

    result = data['results']['bindings']
    return result


def process_id_category_query(data):
    ids = dict()
    for item in data:
        identifier = item['l']['value']
        ids[identifier] = set()

    return ids


def process_main_query(data, ids):
    result = {}
    property_label = ""

    for item in data:
        category = item['category']['value'].strip()
        property_label = item['prop_l']['value'].strip()
        source = item['source']['value'].strip()
        prop_value = item['prop_value']['value'].strip()
        know_as = item['know_as']['value'].strip() if 'know_as' in item.keys() else None
        subject_l = item['source_l']['value'].strip()
        id = item['id']['value'].strip()
        id_l = item['id_l']['value'].strip()
        id_value = item['id_value']['value'].strip()

        if source not in result.keys():
            result[source] = dict()
            result[source]['source'] = source
            result[source]['category'] = set()
            result[source]['prop_value'] = set()
            result[source]['subject_label'] = set()
            result[source]['value_label'] = set()
            result[source].update(copy.deepcopy(ids))

        result[source]['prop_value'].add(prop_value)
        result[source]['category'].add(category)
        result[source]['subject_label'].add(subject_l)
        result[source]['value_label'].add(know_as)
        result[source][id_l].add(id_value)

    # pprint(result)
    return result, property_label


if __name__ == '__main__':
    property = read_args()

    main_query_encoded = encode_url(formulate_main_query(property))
    id_category_encoded = encode_url(formulate_id_category_query(property))

    prefix = 'https://query.wikidata.org/sparql?query='
    format = '&format=json'
    print(prefix + main_query_encoded + format)
    main_query_req = urllib.request.Request(prefix + main_query_encoded + format)

    print(prefix + id_category_encoded + format)
    id_category_query_req = urllib.request.Request(prefix + id_category_encoded + format)

    ids = process_id_category_query(get_query_result(id_category_query_req))

    result, property_label = process_main_query(get_query_result(main_query_req), ids)
    property_label = re.sub(r"\s+", '_', property_label)

    sep = ";"
    with open(property + "_" + property_label + '.csv', 'w') as f:
        values = list(result.values())
        w = csv.DictWriter(f, values[0].keys())
        w.writeheader()
        for k, v in result.items():
            v['value_label'] = list(filter(None, v['value_label']))
            v['value_label'] = list() if not any(v['value_label']) else list(v['value_label'])
            # v['subject_label'] = list(v['subject_label'])
            # v['prop_value'] = list(v['prop_value'])
            # v['category'] = list(v['category'])
            for k1, v1 in v.items():
                if k1 != "source":
                    # print(k1, v1)
                    v[k1] = sep.join(v1)
            w.writerow(v)
