# Streamlit Annotation Visualizer Configuration File
# for Brat Project Exports
#
# default tables in database: annotators, sentences, documents, annotation_types, layers
#
# default columns for entities: id, annotator, begin, end, text, sentence, document, type
# default columns for relations: id, annotator
#
# default indexed columns for entities: type, sentence
#
# default foreign keys for entities (cross table references):
#   annotator -> annotators (id),
#   sentence -> sentences (id),
#   type -> annotation_types (id)
#
# default foreign keys for relations (cross table references):
#   annotator -> annotators (id),
#
#
# all that is configured here is to be seen as an addition to the database structure

additional_database_info = {
    "entities": {  # <- contains all actual annotations in brat that coincide with one or more tokens
        "deid_entities": {  # <- key has to conform to a "layers" key
            "type": "entities",  # <- every annotation needs a type, this maps it to the brat internal name
            "additional_columns": {},
            "indexed_columns": [],
            "reference_columns": {}
        }
    },
    "relations": {

    }
}
# ToDo: describe SQLite data types

# layers lists all annotation layers and their relation in the brat project that should be used in the visualizer
layers = {
    "deid_entities": "entities"
}
