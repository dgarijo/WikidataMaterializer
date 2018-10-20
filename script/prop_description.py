import urllib.request
import sys
import csv
import copy
import json
from typing import List
from pprint import pprint
import re


template_path = "../json_template/desc_template.json"


def read_args():
    property = ""
    if len(sys.argv) > 1:
        property = sys.argv[1].strip()

    return property


def read_template():
    desc_template = dict()
    with open(template_path, 'r') as f:
        desc_template = json.loads(f.read())

    return desc_template


def get_query_result(query_req) -> List[dict]:
    data = {}
    with urllib.request.urlopen(query_req) as r:
        data = json.loads(r.read().decode('utf-8'))

    result = data['results']['bindings']
    return result


def get_property_attr_query(property):
    property_attr_query = 'select distinct ?desc ?prop_label WHERE \
        {\
          wd:' + property + ' schema:description ?desc.\
          filter (lang(?desc)="en")\
          wd:' + property + ' rdfs:label ?prop_label.\
          filter (lang(?prop_label)="en")\
        }'

    return property_attr_query


def get_identifier_attr_query(property):
    identifier_attr_query =  \
        'SELECT DISTINCT ?identifier ?id_l ?desc ?type WHERE \
        {\
          ?source wdt:' + property + '?prop_value.\
          ?source ?id ?id_value.\
          ?identifier a ?type.\
          ?identifier schema:description ?desc.\
          filter (lang(?desc)="en")\
          ?identifier wikibase:directClaim ?id.\
          ?identifier wikibase:propertyType wikibase:ExternalId.\
          ?identifier rdfs:label ?id_l.\
          filter (lang(?id_l)="en")\
        }\
        ORDER BY ?identifier'

    return identifier_attr_query


def fill_description(desc_template, data):
    data = data[0]
    desc_template['title'] = desc_template['title'] + data['prop_label']['value'].upper()
    desc_template['description'] = data['desc']['value']
    desc_template['url'] = desc_template['url'] + property
    return desc_template


def encode_url(url):
    encoded_url = urllib.parse.quote(url)
    return encoded_url


def process_property_attr_query(desc_template, data):
    variables = list()
    for item in data:
        # print(item)
        # assemble variable
        variable = dict()
        variable['name'] = item['id_l']['value']
        variable['description'] = item['desc']['value']
        variable.setdefault('semantic_type', []).append(item['type']['value'])
        variable['external_identifier'] = ""
        variable['named_entity'] = list()
        variable['temporal_coverage']= \
            { 
                "start": "",
                "end": ""
            }
        variable['spatial_coverage'] = ""
        variables.append(variable)

    desc_template['variables'] = variables
    return desc_template


if __name__ == '__main__':
    property = read_args()

    property_attr_query_encoded = encode_url(get_property_attr_query(property))
    identifier_attr_query_encoded = encode_url(get_identifier_attr_query(property))

    prefix = 'https://query.wikidata.org/sparql?query='
    format = '&format=json'

    print("property_attr_query ", prefix + property_attr_query_encoded + format)
    property_attr_query = urllib.request.Request(prefix + property_attr_query_encoded + format)

    print("identifier_attr ", prefix + identifier_attr_query_encoded + format)
    identifier_attr_query = urllib.request.Request(prefix + identifier_attr_query_encoded + format)

    desc_template = read_template()

    desc_template = fill_description(desc_template, get_query_result(property_attr_query))

    desc_template = process_property_attr_query(desc_template, get_query_result(identifier_attr_query))

    pprint(desc_template)
