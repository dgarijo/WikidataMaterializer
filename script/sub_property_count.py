import urllib.request
import sys
import csv
import copy
import json
from typing import List
from pprint import pprint

main_query = 'select ?prop where{\
    ?prop a owl:ObjectProperty. \
    filter (regex(str(?prop), "^http://www.wikidata.org/prop/direct/"))\
    }'

encoded_url = urllib.parse.quote(main_query)

prefix = 'https://query.wikidata.org/sparql?query='
format = '&format=json'

url = prefix + encoded_url + format

print(url)

id_category_query_req = urllib.request.Request(url)

data = {}
with urllib.request.urlopen(id_category_query_req) as r:
    data = json.loads(r.read().decode('utf-8'))

result = data['results']['bindings']

properties = list()

for record in result:
    properties.append(record['prop']['value'])

print(len(properties))

count_map = dict()

retrievable, unretrievable = 0, 0

for prop in properties:
    count_sub_query = 'select (count(distinct ?sub) as ?num) where{\
		?sub <' + prop + '> ?val.\
    }'
    count_sub_url = prefix + urllib.parse.quote(count_sub_query) + format
    count_sub_req = urllib.request.Request(count_sub_url)

    count_data = {}
    try:
        with urllib.request.urlopen(count_sub_req) as r:
            count_data = json.loads(r.read().decode('utf-8'))
            count = int(count_data['results']['bindings'][0]['num']['value'])
        count_map[prop] = count
        retrievable += 1
        print(prop, " ", count_map[prop])
    except Exception as e:
        unretrievable += 1
        continue

sorted_by_value = sorted(count_map.items(), key=lambda kv: kv[1])
pprint(sorted_by_value)
print("retrieved: ", retrievable)
print ("unretrieved: ", unretrievable)
