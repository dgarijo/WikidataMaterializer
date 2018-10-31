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

    result = data["results"]["bindings"]
    return result


# egt property label & description
def get_property_attr_query(property):
    property_attr_query = 'select distinct ?desc ?prop_label WHERE \
        {\
          wd:' + property + ' schema:description ?desc.\
          filter (lang(?desc)="en")\
          wd:' + property + ' rdfs:label ?prop_label.\
          filter (lang(?prop_label)="en")\
        }'

    return property_attr_query


# get categories for all sources
def get_source_category(property):
    source_category = \
    'SELECT DISTINCT ?source (group_concat(distinct ?category_l ; separator=";") as ?cat_labels) WHERE \
        {\
          ?source wdt:' + property +' ?prop_value.\
          ?source wdt:P31 ?category.\
          ?category rdfs:label ?category_l.\
          filter (lang(?category_l)="en")\
          ?source ?id ?id_value.\
          ?identifier a ?type.\
          ?identifier schema:description ?desc.\
          filter (lang(?desc)="en")\
          ?identifier wikibase:directClaim ?id.\
          ?identifier wikibase:propertyType wikibase:ExternalId.\
          ?identifier rdfs:label ?id_l.\
          filter (lang(?id_l)="en")\
        }\
        GROUP BY ?source'

    return source_category


# get categories for all object values
def get_prop_value_category(property):
    source_category = \
        'SELECT DISTINCT ?prop_value (group_concat(distinct ?category_l ; separator=';') as ?cat_labels) WHERE \
            {\
              ?source wdt:' + property + ' ?prop_value.\
              ?source wdt:P31 ?category.\
              ?prop_value rdfs:label ?category_l.\
              filter (lang(?category_l)="en")\
              ?source ?id ?id_value.\
              ?identifier a ?type.\
              ?identifier schema:description ?desc.\
              filter (lang(?desc)="en")\
              ?identifier wikibase:directClaim ?id.\
              ?identifier wikibase:propertyType wikibase:ExternalId.\
              ?identifier rdfs:label ?id_l.\
              filter (lang(?id_l)="en")\
            }\
            GROUP BY ?source'

    return source_category


# get information from identifier
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
    desc_template["title"] = desc_template["title"] + data["prop_label"]["value"].upper()
    desc_template["description"] = data["desc"]["value"]
    desc_template["url"] = desc_template["url"] + property
    return desc_template


def encode_url(url):
    encoded_url = urllib.parse.quote(url)
    return encoded_url


def process_property_attr_query(desc_template, data, mapping):
    variables = list()
    for item in data:
        # print(item)
        # assemble variable
        variable = dict()
        variable["wikidata_identifier"] = item["identifier"]["value"]
        prop_id = variable["wikidata_identifier"].split("/")[-1]
        variable["external_source_ns"] = mapping.get(prop_id, "")
        variable["name"] = item["id_l"]["value"]
        variable["description"] = item["desc"]["value"]
        variable["semantic_type"] = "string"
        # variable["external_identifier"] = ""
        variable["named_entity"] = list()
        variable["temporal_coverage"]= \
            { 
                "start": "",
                "end": ""
            }
        variable["spatial_coverage"] = ""
        variables.append(variable)

    desc_template["variables"] = variables
    return desc_template


def get_ext_id_namespace_query(property):
    ext_id_namespace_query = \
    'SELECT DISTINCT ?p (group_concat(?v; separator = ";") as ?v_concat) WHERE \
    { \
        ?source wdt:' + property + ' ?prop_value. \
        ?source ?p ?v. \
            BIND(STR(?p) AS ?string ). \
        filter(regex(str(?p), "direct-normalized")) \
    } group by ?p'

    return ext_id_namespace_query


def process_ext_id_namespace_query(data):
    mapping = dict()
    for item in data:
        external_id = item["p"]["value"].split("/")[-1]
        urls = item["v_concat"]["value"].split(";")
        namespace = urls[0].rsplit('/', 1)[0]
        mapping[external_id] = namespace

    return mapping


if __name__ == '__main__':
    property = read_args()

    property_attr_query_encoded = encode_url(get_property_attr_query(property))
    identifier_attr_query_encoded = encode_url(get_identifier_attr_query(property))
    ext_id_namespace_query_encoded = encode_url(get_ext_id_namespace_query(property))

    prefix = 'https://query.wikidata.org/sparql?query='
    format = '&format=json'

    print("property_attr_query ", prefix + property_attr_query_encoded + format)
    property_attr_query = urllib.request.Request(prefix + property_attr_query_encoded + format)

    print("identifier_attr ", prefix + identifier_attr_query_encoded + format)
    identifier_attr_query = urllib.request.Request(prefix + identifier_attr_query_encoded + format)

    print("identifier namespace mapping ", prefix + ext_id_namespace_query_encoded + format)
    ext_id_namespace_query = urllib.request.Request(prefix + ext_id_namespace_query_encoded + format)

    # -------------------------- #

    desc_template = read_template()

    desc_template = fill_description(desc_template, get_query_result(property_attr_query))

    mapping = process_ext_id_namespace_query(get_query_result(ext_id_namespace_query))

    desc_template = process_property_attr_query(desc_template, get_query_result(identifier_attr_query), mapping)

    pprint(desc_template)
