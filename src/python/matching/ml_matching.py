import os, sys, inspect
sys.path.insert(0, os.path.realpath(os.path.abspath(os.path.join(os.path.split(inspect.getfile( inspect.currentframe() ))[0],".."))))
import codecs
import psycopg2
import psycopg2.extras
import csv
from pprint import pprint
import operator
import string
import itertools
import operator
import util.path_tools
import re
import argparse
import util.amend_earmark
import logging
from matching_util import *
import util.amend_earmark
from sklearn.externals import joblib


import multiprocessing as mp

from matching.feature_generators.jaccard_feature_generator import JaccardFeatureGenerator
from matching.feature_generators.ranking_feature_generator import RankingFeatureGenerator
from matching.feature_generators.difference_feature_generator import DifferenceFeatureGenerator
from matching.feature_generators.infix_feature_generator import InfixFeatureGenerator
from classification import pipe
from classification.pipe import Pipe
from classification.blocks_pipe import BlocksPipe
from classification.instances_grouper import InstancesGrouper

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
 


MIN = 0.1
 


CONN_STRING = "dbname=harrislight user=harrislight password=harrislight host=dssgsummer2014postgres.c5faqozfo86k.us-west-2.rds.amazonaws.com"

def get_doc_ids_from_db(year):

    conn = psycopg2.connect(CONN_STRING)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("select distinct document_id from earmark_documents, documents where documents.id = earmark_documents.document_id and extract(year from date) = %s ", (year, ))
    docs = cur.fetchall()
    conn.close()
    return [d[0] for d in docs]


def get_earmark_ids_in_doc(doc_id):
    conn = psycopg2.connect(CONN_STRING)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("select distinct earmark_id from earmark_documents where document_id = %s", (doc_id, ))
    earmarks = cur.fetchall()
    conn.close()
    return [e[0] for e in earmarks]



def get_entity_ids_in_doc_from_db(doc_id):
    conn = psycopg2.connect(CONN_STRING)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("select distinct id from entities where document_id = %s and entity_type = 'table_row'", (doc_id, ))
    entities = cur.fetchall()
    conn.close()
    return [e[0] for e in entities]


def get_earmark_entity_tuples(earmark_ids, entity_ids):
    earmark_entity_tuples = []
    for entity_id in entity_ids:
        for earmark_id in earmark_ids:
            earmark_entity_tuples.append((entity_id, earmark_id, 1))
    return earmark_entity_tuples

   


def record_matching (instances, y_pred):
    """
    If matching was succesfull, update the inferred_offest in DB"
    """
    conn = psycopg2.connect(CONN_STRING)
    cur = conn.cursor()
    params = []

    for i in range(len(instances)):
        if y_pred[i] == 1:
            instance = instances[i]
            entity = instance.attributes['entity'].entity
            earmark = instance.attributes['earmark'].earmark
            offset = entity.entity_offset
            length = entity.entity_length
            entity_id = entity.id
            earmark_id = earmark.earmark_id

            earmark_document_id = util.amend_earmark.check_earmark_doc_match(earmark_id, entity_id)
            params.append((earmark_document_id, entity_id, earmark_document_id, entity_id))


    cmd = """insert into earmark_document_matched_entities 
    (earmark_document_id,matched_entity_id ,manual_match)
    select %s, %s, False
    WHERE NOT EXISTS 
    (SELECT 1 FROM earmark_document_matched_entities WHERE earmark_document_id=%s and matched_entity_id = %s );
    """

    logging.debug("Inserting for entity %d and earmark %d" %(entity_id, earmark_id))
    cur.executemany(cmd, params)
    conn.commit()
    conn.close()



def get_features(instances, num_processes):
    logging.info("Creating pipe")

    fgs = [
        JaccardFeatureGenerator(),
        InfixFeatureGenerator()
    ]
    pipe = Pipe(fgs, instances, num_processes=num_processes)
    logging.info("Pushing into pipe")
    pipe.push_all_parallel()

    #group by earmark
    fgs = [
        RankingFeatureGenerator(feature_group = "JACCARD_FG", feature ="JACCARD_FG_max_inferred_name_jaccard" , prefix = 'G2_'),
        RankingFeatureGenerator(feature_group = "JACCARD_FG", feature ="JACCARD_FG_max_cell_jaccard" , prefix = 'G1_')
    ]
    grouper = InstancesGrouper(['earmark_id'])
    pipe = BlocksPipe(grouper, fgs, pipe.instances, num_processes=num_processes )
    pipe.push_all_parallel()

    return pipe.instances




def process_document(args_tuple):


    doc_id = args_tuple[0]
    logging.info("Processing Document %d" %doc_id )

    earmark_ids = get_earmark_ids_in_doc(doc_id)[:10]
    logging.info("Got %d earmarks" % len(earmark_ids))

    entity_ids = get_entity_ids_in_doc_from_db(doc_id)[:10]
    logging.info("Got %d entities" % len(entity_ids))

    earmark_entity_tuples = get_earmark_entity_tuples(earmark_ids, entity_ids)
    instances = get_matching_instances(entity_ids, earmark_ids, earmark_entity_tuples, 1)
    logging.info("Got %d Instances" % len(instances))

    if len(instances) == 0:
        return


    #compute features
    instances = get_features(instances, 1)

    logging.info("Got Features")

    #convert to scipy
    X, y, space = pipe.instances_to_scipy_sparse(instances)

    #deserialize model and predict

    model = joblib.load(args_tuple[2])
    logging.info("Loaded Models")


    y_pred = model.predict(X.todense())
    logging.info("Got Predictions Models")


    #record predictionsin db
    if args_tuple[1]:
        record_matching(instances, y_pred)
        logging.info("Updated DB")



    
def main():

    parser = argparse.ArgumentParser(description='Match entities to OMB')
    parser.add_argument('--year', required=True, type=int, help='which year to match')
    parser.add_argument('--threads', type=int, default = 8, help='number of threads to run in parallel')
    parser.add_argument('--update', action='store_true',default = False,  help = 'record matches in db')
    parser.add_argument('--model', required = True, help='path to pickeld matching model')


    args = parser.parse_args()
    
    print "Process id: ", os.getpid()

    doc_ids = get_doc_ids_from_db(args.year)

    for doc_id in doc_ids:
        process_document((doc_id, args.update, args.model))

    #p = mp.Pool(args.threads)
    #results = p.map(process_document, [(doc_id, args.update) for doc_id in doc_ids])

   
    


if __name__=="__main__":

    main()
