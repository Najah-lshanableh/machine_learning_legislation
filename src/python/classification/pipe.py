"""
mallet equivelant of serial pipe
to generate x and y to be used in sciket learn classification
"""
import os, sys, inspect
sys.path.insert(0, os.path.realpath(os.path.abspath(os.path.join(os.path.split(inspect.getfile( inspect.currentframe() ))[0],".."))))
import argparse
from pprint import pprint
import psycopg2
import logging
import numpy as np
import scipy
import multiprocessing as mp


def parallel_target(pipe_instance_tuple):
    pipe = pipe_instance_tuple[0]
    instance = pipe_instance_tuple[1]
    new_instance = pipe(instance)
    parallel_target.queue.put(new_instance)
    
def initilize_parallel(q):
    """
    q: queue object
    """
    #http://stackoverflow.com/questions/3827065/can-i-use-a-multiprocessing-queue-in-a-function-called-by-pool-imap
    parallel_target.queue = q

class Pipe:
    def __init__(self, feature_generators=[], instances=[], num_processes = 1):
        """
        accepts a list of instances of abstract_feature_generator
        """
        self.feature_generators = feature_generators
        self.instances = instances
        self.num_processes = num_processes
        
    def push_single(self, instance):
        """
        pushes instance through the pipe of feature generators
        """
        #logging.debug("operating on instance")
        for fg in self.feature_generators:
            fg.operate(instance)
        # return statement is added to support multiprocessing
        return instance
    
    def __call__(self, instance):
        return self.push_single(instance)
            
    def push_all(self):
        for i in self.instances:
            self.push_single(i)
            
    def push_all_parallel(self):
        if self.num_processes == 1:
            logging.info("pushing through pipe with no pool")
            self.push_all()
        else:
            logging.info("creating thread pool with %d threads" %(self.num_processes))
            out_queue = mp.Queue()
            pool = mp.Pool(self.num_processes, initilize_parallel, [out_queue])
            pool.map(func=parallel_target, iterable= [(self, i) for i in self.instances])
            new_instances = []
            for i in range(len(self.instances)):
                new_instances.append(out_queue.get())
            del out_queue
            del self.instances[:]
            self.instances = new_instances
        

            
    def set_instances(self, instances):
        self.instances = instances



    def instances_to_matrix(self, groups=None, dense = False):
        if not goups:
            groups = self.instances[0].feature_groups.keys()
        return instances_to_scipy_sparse(self.instances, groups=groups)
    
            
            
def instances_to_matrix(instances, groups= None, feature_space=None, dense = False):
    """
    ingore_groups: list containing generator names to ignore their features
    """

    if not groups:
        groups = instances[0].feature_groups.keys()

    use_given_feature_space = True

    if feature_space == None:
        use_given_feature_space = False
        feature_space = build_feature_space(instances, groups=groups)


    logging.debug("%d instances, %d features" %(len(instances), len(feature_space)))
    X = scipy.sparse.lil_matrix((len(instances), len(feature_space)))
    Y = []
    for i in range(len(instances)):
        for f_group, features in instances[i].feature_groups.iteritems():
            if f_group not in groups and not use_given_feature_space:
                continue
            for f_name, f in features.iteritems():
                if not f.name in feature_space:
                    #logging.warning("%s is not in the feature space, ignoring!"%(f.name))
                    pass
                else:
                    X[i, feature_space[f.name]] =  f.value
        Y.append(instances[i].target_class)
    logging.debug("%d Instances loaded with %d features" %(X.shape[0], X.shape[1]))

    if not dense:
        return scipy.sparse.csr_matrix(X), np.array(Y), feature_space 
    else:
        return X.todense(), np.array(Y), feature_space 


    
def build_feature_space(instances, groups=[]):
    feature_space = {}
    index = 0
    for i in instances:
        for f_group, features in i.feature_groups.iteritems():
            if f_group not in groups:
                continue
            for f_name, f in features.iteritems():
                if not feature_space.has_key(f.name):
                    feature_space[f.name] = index
                    index +=1
    return feature_space
    
