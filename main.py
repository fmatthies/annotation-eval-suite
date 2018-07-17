# -*- coding: utf-8 -*-

from compare import comparison
from compare import centroids
DEBUG = False

#FINDEX_STRING = "test_resources/file_index"
#SET_LIST = ["data1/alt","data2"]
#ROOT_STRING = "test_resources/"

#FINDEX_STRING = "C:\\Users\\F00708\\Documents\\medical\\agreement\\agreement_index"
#SET_LIST = ["d.dickopf", "f.just", "k.bunz", "t.rocktaeschel"]
#ROOT_STRING = "C:\\Users\\F00708\\Documents\\medical\\agreement"

#FINDEX_STRING = "/home/matthies/SMITH/Jena-TMP/first_fifteen/file_index"
#SET_LIST = ["d.dickopf", "e.sobe", "f.just", "k.bunz", "t.rocktaeschel"]
#ROOT_STRING = "/home/matthies/SMITH/Jena-TMP/first_fifteen"

#FINDEX_STRING = "test_resources/file_index_centroid"
#SET_LIST = ["data1/centroid", "data2/centroid", "data3/centroid"]
#ROOT_STRING = "test_resources/"

#FINDEX_STRING = "/home/matthies/STAKI/agreement/agreement_index"
#SET_LIST = ["d.dickopf", "e.sobe", "f.just", "k.bunz", "t.rocktaeschel"]
#ROOT_STRING = "/home/matthies/STAKI/agreement/"

#FINDEX_STRING = "/home/matthies/workspaces/github/brat-al/data/testing/test_index"
#SET_LIST = ["data1", "data2", "data3"]
#ROOT_STRING = "/home/matthies/workspaces/github/brat-al/data/testing/"

FINDEX_STRING = "/home/matthies/STAKI/agreement/02/agreement_index"
SET_LIST = ["d.dickopf", "e.sobe", "f.just", "k.bunz", "t.rocktaeschel"]
ROOT_STRING = "/home/matthies/STAKI/agreement/02/"

if __name__ == "__main__":
    cbatch = comparison.BatchComparison(FINDEX_STRING, SET_LIST, ROOT_STRING)
    #cbatch.print_agreement(trigger='Token', match_type='one_all', threshold=2, boundary=0)

    if DEBUG:
        print("DEBUGGING")
        c = cbatch.get_comparison_obj("centroid_test")
        [_c.print_self() for _c in
         c.return_errors(trigger="Medication", match_type="one_all", error_type="both", threshold=2, boundary=0,
                         focus_annotator="data3")]
        #cbatch.print_agreement(trigger="Medication", match_type='one_all')
        #dociter = cbatch.doc_iterator()
        #[_c.print_self() for _c in
        # cbatch.get_comparison_obj("centroid_test").return_errors(match_type='one_all', error_type='both', threshold=1)]
        #cbatch.print_agreement(next(dociter), "All", False)
        #cbatch.print_agreement(next(dociter))
        #cbatch.print_agreement(trigger="All")
        #comp_obj = cbatch.get_comparison_obj(next(dociter))
        #print("break")
        #centroid = centroids.Centroids(comp_obj)
        #comp_obj.print_agreement_scores(match_type='approximate', boundary=1)
